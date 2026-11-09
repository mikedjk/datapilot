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