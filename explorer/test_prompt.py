import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlite3
import config
from prompts import build_system_prompt
from llm_client import LLMClient

conn = sqlite3.connect(config.DB_PATH)
schema = "\n\n".join(r[0] for r in conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"))
prompt = build_system_prompt(schema)
llm = LLMClient(config.LLM_MODEL, config.OLLAMA_URL)

for q in ["Combien de commandes ont été livrées en 2025 ?",
          "Quelle est la politique de retour pour les clients VIP ?",
          "Bonjour, qui es-tu ?"]:
    print(q, "->", llm.chat([{"role": "system", "content": prompt},
                             {"role": "user", "content": q}], json_mode=True))
    print()
print(len(prompt), "caractères, environ", len(prompt) // 4, "tokens")