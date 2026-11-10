"""ui.py — Interface Gradio de DataPilot (couche présentation uniquement)."""
from __future__ import annotations

import logging

import gradio as gr

TITLE = "DataPilot — l'assistant data analyst de ShopNova"
DESCRIPTION = (
    "Posez vos questions en français sur les **ventes ShopNova 2024-2025** (chiffre d'affaires, "
    "clients, retours, canaux…) ou sur les **règles internes** (définition des indicateurs, "
    "politique de retours, livraison, segments clients). Chaque réponse s'appuie sur la base de "
    "données ou la documentation : dépliez les blocs 🔧 pour voir la requête exécutée ou les "
    "passages consultés."
)
FOOTER = (
    "<small>Données de démonstration (ventes 2024-2025). L'assistant peut se tromper : "
    "vérifiez les requêtes affichées avant toute décision. Une réponse peut prendre "
    "une à deux minutes.</small>"
)
EXAMPLES = [
    "Quel est le chiffre d'affaires net de 2025 ?",                  # chiffrée
    "Combien de clients ont le statut VIP ?",                        # chiffrée
    "Quel est le délai de retour pour un client VIP ?",              # règle
    "À partir de quel montant la livraison est-elle offerte ?",      # règle
    "Quel est le panier moyen 2025 selon la définition officielle ?",  # mixte
    "Quel est le taux de retour 2025 ?",                             # mixte
]

# Libellés des outils (les icônes seront personnalisées à l'étape 13)
TOOL_LABELS = {"query_database": "Requête SQL", "search_docs": "Recherche documentaire"}
MAX_RESULT_CHARS = 1500


def message_text(content) -> str:
    """Gradio 6 peut renvoyer le contenu d'un message sous forme de liste de morceaux."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for chunk in content:
            if isinstance(chunk, dict) and "text" in chunk:
                parts.append(str(chunk["text"]))
        return " ".join(parts)
    return str(content)


def _truncate(text: str, limit: int = MAX_RESULT_CHARS) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "\n… (tronqué)"


def steps_to_messages(steps) -> list[dict]:
    """Transforme les étapes de l'agent en blocs repliables pour le Chatbot."""
    messages = []
    for step in steps:
        if step.kind == "tool":
            label = TOOL_LABELS.get(step.tool, step.tool)
            if step.tool == "query_database":
                entree = f"```sql\n{step.tool_input}\n```"
            else:
                entree = f"Recherche : {step.tool_input}"
            messages.append({
                "role": "assistant",
                "content": f"{entree}\n\n**Résultat**\n\n{_truncate(step.content)}",
                "metadata": {"title": f"🔧 {label}", "status": "done"},
            })
        elif step.kind == "error":
            messages.append({
                "role": "assistant",
                "content": _truncate(step.content),
                "metadata": {"title": "⚠️ Réponse du modèle à corriger", "status": "done"},
            })
        # les étapes « final » sont ignorées : la réponse est ajoutée à part
    return messages


def create_ui(agent) -> gr.Blocks:
    """`agent` : tout objet avec ask(question) -> (answer, steps) et reset()."""

    def add_user_message(message: str, history: list):
        if not message or not message.strip():
            return "", history
        return "", history + [{"role": "user", "content": message}]

    def bot_response(history: list):
        if not history or history[-1]["role"] != "user":
            return history
        question = message_text(history[-1]["content"])
        response = agent.ask(question)
        return (history + steps_to_messages(response.steps)
                + [{"role": "assistant", "content": response.answer}])

    def reset_conversation():
        agent.reset()
        return [], ""

    with gr.Blocks(title="DataPilot") as demo:
        gr.Markdown(f"# {TITLE}")
        gr.Markdown(DESCRIPTION)
        chatbot = gr.Chatbot(label="Conversation", height=520,
                             placeholder="Posez une question ou cliquez sur un exemple 👇",
                             buttons=["copy"])
        with gr.Row():
            question = gr.Textbox(show_label=False, scale=8, placeholder="Votre question…")
            send_btn = gr.Button("Envoyer", variant="primary", scale=1)
            reset_btn = gr.Button("🔄 Réinitialiser", scale=1)
        gr.Examples(examples=EXAMPLES, inputs=question, label="Exemples de questions")
        gr.Markdown(FOOTER)

        # Deux événements enchaînés : la question s'affiche tout de suite (rapide),
        # puis l'agent calcule la réponse (lent) pendant que Gradio montre un chargement.
        for trigger in (question.submit, send_btn.click):
            trigger(add_user_message, [question, chatbot], [question, chatbot],
                    queue=False).then(bot_response, chatbot, chatbot, show_progress="full")
        reset_btn.click(reset_conversation, None, [chatbot, question], queue=False)
    return demo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from agent import build_agent

    agent, llm = build_agent()
    if not llm.is_available():
        print("⚠️ Ollama ne répond pas : lancez l'application Ollama ou 'ollama serve'.")
    create_ui(agent).launch(theme=gr.themes.Soft())
