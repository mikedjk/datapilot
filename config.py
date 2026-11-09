"""config.py — Paramètres centralisés du projet DataPilot."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # dossier qui contient ce fichier

# --- Moteur LLM (Ollama) ----------------------------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
LLM_NUM_CTX = int(os.getenv("LLM_NUM_CTX", "8192"))  # fenêtre de contexte (tokens)

# --- Données ----------------------------------------------------------
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "ecommerce.db"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", BASE_DIR / "data" / "docs"))

# --- Recherche documentaire (RAG) -------------------------------------
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 500     # taille max d'un morceau (caractères)
CHUNK_OVERLAP = 100  # chevauchement entre deux morceaux
TOP_K = 3            # nombre de passages renvoyés par la recherche

# --- Agent ------------------------------------------------------------
MAX_STEPS = 5          # étapes max (appels d'outils) par question
MAX_HISTORY_TURNS = 6  # tours (question + réponse) gardés en mémoire
SQL_MAX_ROWS = 50      # lignes max renvoyées par une requête SQL

# --- Journaux ---------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"