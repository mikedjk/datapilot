"""agent.py — Routing et boucle de l'agent DataPilot."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from llm_client import Conversation, LLMError

logger = logging.getLogger("agent")

FINAL = "final_answer"


@dataclass
class Decision:
    action: str
    input: object
    thought: str = ""
    params: list = field(default_factory=list)


class ParseError(ValueError):
    """La sortie du LLM n'est pas une décision lisible."""


def parse_llm_output(raw: str) -> Decision:
    """Transforme le texte du LLM en Decision, en étant tolérant sur la forme."""
    # 1. retirer les balises de code markdown éventuelles
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 2. essayer le JSON tel quel ; sinon extraire du premier « { » au dernier « } »
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)  # gourmand : garde les objets imbriqués
        if not match:
            raise ParseError("aucun objet JSON trouvé dans la réponse du LLM.")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ParseError(f"JSON invalide : {exc}") from exc

    # 3. vérifier la structure
    if not isinstance(data, dict) or "action" not in data:
        raise ParseError("le JSON ne contient pas la clé « action ».")

    params = data.get("params") or []
    return Decision(
        action=str(data["action"]).strip().lower(),
        input=data.get("input", data.get("action_input", "")),
        thought=str(data.get("thought", "")),
        params=params if isinstance(params, list) else [],
    )


@dataclass
class RouteResult:
    kind: str                 # "tool", "final" ou "error"
    content: str
    tool: str | None = None
    tool_input: object = None
    thought: str = ""


def route_query(llm_output: str, tools: dict) -> RouteResult:
    """Lit la décision du LLM et exécute l'outil demandé. Ne lève jamais d'exception."""
    # Cas 1 : JSON illisible -> message d'erreur pour le LLM
    try:
        decision = parse_llm_output(llm_output)
    except ParseError as exc:
        return RouteResult(
            kind="error",
            content=(f"Réponse illisible ({exc}) Réponds UNIQUEMENT avec un objet JSON de la forme "
                     '{"thought": "...", "action": "...", "input": "..."}, sans aucun texte autour.'),
        )

    # Cas 2 : réponse finale
    if decision.action == FINAL:
        return RouteResult(kind="final", content=str(decision.input), thought=decision.thought)

    # Cas 3 : outil inconnu
    if decision.action not in tools:
        valides = ", ".join([*tools, FINAL])
        return RouteResult(
            kind="error",
            content=f"Outil inconnu « {decision.action} ». Outils valides : {valides}.",
            tool=decision.action,
            thought=decision.thought,
        )

    # Cas 4 : outil connu -> on l'exécute (avec params si c'est du SQL paramétré)
    tool = tools[decision.action]
    if decision.action == "query_database" and decision.params:
        result = tool.run(str(decision.input), decision.params)
    else:
        result = tool.run(str(decision.input))
    return RouteResult(
        kind="tool",
        content=result,
        tool=decision.action,
        tool_input=decision.input,
        thought=decision.thought,
    )



@dataclass
class AgentResponse:
    answer: str
    steps: list[RouteResult] = field(default_factory=list)


class Agent:
    """Boucle ReAct : le LLM décide -> route_query exécute -> OBSERVATION -> ..."""

    def __init__(self, llm, tools: dict, system_prompt: str,
                 max_steps: int = 5, max_history_turns: int = 6) -> None:
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.conversation = Conversation(system_prompt, max_turns=max_history_turns)

    def ask(self, question: str) -> AgentResponse:
        self.conversation.add_user(question)
        scratchpad = self.conversation.messages()   # copie : le brouillon est jetable
        steps: list[RouteResult] = []
        answer = None

        try:
            for _ in range(self.max_steps):
                raw = self.llm.chat(scratchpad, json_mode=True)
                result = route_query(raw, self.tools)
                steps.append(result)
                logger.info("étape %d : %s %s", len(steps), result.kind, result.tool or "")

                if result.kind == "final":
                    answer = result.content
                    break

                # Sinon : le LLM doit voir ce qu'il a demandé ET le résultat
                scratchpad.append({"role": "assistant", "content": raw})
                if result.kind == "error":
                    observation = f"ERREUR DE FORMAT : {result.content}"
                else:
                    observation = f"OBSERVATION ({result.tool}) :\n{result.content}"
                scratchpad.append({"role": "user", "content": observation})

            if answer is None:
                # Limite atteinte : on force une réponse finale avec ce qu'on a
                scratchpad.append({
                    "role": "user",
                    "content": ("Tu as atteint la limite d'étapes. Donne maintenant ta réponse "
                                "finale avec les informations déjà obtenues (action "
                                "final_answer). Si elles sont insuffisantes, dis-le clairement."),
                })
                raw = self.llm.chat(scratchpad, json_mode=True)
                result = route_query(raw, self.tools)
                steps.append(result)
                answer = (result.content if result.kind == "final" else
                          "Désolé, je n'ai pas réussi à répondre à cette question. "
                          "Pouvez-vous la reformuler ?")
        except LLMError as exc:
            logger.error("LLM indisponible : %s", exc)
            answer = ("Le moteur LLM est indisponible. Lancez l'application Ollama "
                      "ou 'ollama serve', puis réessayez.")

        self.conversation.add_assistant(answer)      # seule la réponse finale est mémorisée
        return AgentResponse(answer=answer, steps=steps)

    def reset(self) -> None:
        self.conversation.reset()


def build_agent():
    """Assemble le LLM, les outils, le prompt et l'agent. Renvoie (agent, llm)."""
    import config
    from llm_client import LLMClient
    from prompts import build_system_prompt
    from tools import DocSearchTool, SQLTool, load_corpus, load_embedder

    llm = LLMClient(
        config.LLM_MODEL, config.OLLAMA_URL,
        temperature=config.LLM_TEMPERATURE, timeout=config.LLM_TIMEOUT,
        num_ctx=config.LLM_NUM_CTX,
        log_file=config.LOG_DIR / "llm_exchanges.jsonl",
    )
    sql_tool = SQLTool(config.DB_PATH, max_rows=config.SQL_MAX_ROWS)
    chunks = load_corpus(config.DOCS_DIR, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    doc_tool = DocSearchTool(chunks, load_embedder(config.EMBEDDING_MODEL), top_k=config.TOP_K)
    tools = {sql_tool.name: sql_tool, doc_tool.name: doc_tool}
    system_prompt = build_system_prompt(sql_tool.get_schema())
    agent = Agent(llm, tools, system_prompt,
                  max_steps=config.MAX_STEPS, max_history_turns=config.MAX_HISTORY_TURNS)
    return agent, llm


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent, llm = build_agent()
    if not llm.is_available():
        print("⚠️ Ollama ne répond pas : lancez l'application Ollama ou 'ollama serve'.")
    print("DataPilot — tapez 'quit' pour sortir, 'reset' pour vider la mémoire.")
    while True:
        question = input("\nVous > ").strip()
        if not question:
            continue
        if question.lower() == "quit":
            break
        if question.lower() == "reset":
            agent.reset()
            print("Mémoire vidée.")
            continue
        response = agent.ask(question)
        for i, step in enumerate(response.steps, 1):
            if step.kind == "tool":
                print(f"  [{i}] {step.tool} : {str(step.tool_input)[:100]}")
            elif step.kind == "error":
                print(f"  [{i}] ⚠️ erreur : {step.content[:100]}")
        print(f"\nDataPilot > {response.answer}")