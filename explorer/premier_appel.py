"""explorer/premier_appel.py — Premier appel HTTP à Ollama."""
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pour importer config
import config

payload = {
    "model": config.LLM_MODEL,
    "messages": [
    {"role": "user", "content": "Explique en une phrase ce qu'est un panier moyen."},
],
    "stream": False,
    "options": {"temperature": config.LLM_TEMPERATURE},
}

debut = time.perf_counter()
reponse = requests.post(f"{config.OLLAMA_URL}/api/chat", json=payload, timeout=120)
duree = time.perf_counter() - debut

data = reponse.json()
print("Code HTTP        :", reponse.status_code)
print("Réponse          :", data["message"]["content"])
print("Tokens lus       :", data["prompt_eval_count"])
print("Tokens générés   :", data["eval_count"])
print(f"Durée            : {duree:.1f} s")