"""llm_client.py — Client LLM robuste en Python pur (bibliothèque requests)."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger("llm_client")


class LLMError(Exception):
    """Erreur définitive du client LLM (après épuisement des tentatives)."""


class LLMClient:
    RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

    def __init__(self, model, base_url="http://localhost:11434", temperature=0.1,
                 timeout=120, max_retries=3, backoff_factor=1.0, num_ctx=8192,
                 log_file=None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.url = self.base_url + "/api/chat"
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.num_ctx = num_ctx
        self.log_file = Path(log_file) if log_file else None
        self.session = requests.Session()  # réutilise la connexion entre les appels

    def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = "json"

        start = time.perf_counter()
        data = self._post_with_retry(payload)
        duration = time.perf_counter() - start

        try:
            answer = data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Réponse inattendue du serveur LLM : {data!r}") from exc

        self._log_exchange(messages, answer, duration, data)
        return answer

    def _post_with_retry(self, payload: dict) -> dict:
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(self.url, json=payload,
                                             timeout=self.timeout)
                # Erreur temporaire : on la transforme en HTTPError pour la réessayer
                if response.status_code in self.RETRYABLE_STATUS:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}", response=response)
                # Autre erreur : définitive, on s'arrête tout de suite
                if response.status_code >= 400:
                    raise LLMError(
                        f"Erreur HTTP {response.status_code} : {response.text[:200]}")
                try:
                    return response.json()
                except ValueError as exc:
                    raise LLMError("Le serveur n'a pas renvoyé du JSON valide.") from exc
            except (requests.ConnectionError, requests.Timeout,
                    requests.HTTPError) as exc:
                last_error = exc
                if attempt < self.max_retries:  # pas de pause après le dernier essai
                    wait = self.backoff_factor * 2 ** (attempt - 1)
                    logger.warning("Tentative %d/%d échouée (%s). Nouvel essai dans %.1f s.",
                                   attempt, self.max_retries, exc, wait)
                    time.sleep(wait)
        raise LLMError(
            f"Le moteur LLM est injoignable après {self.max_retries} tentatives "
            f"({last_error}). Lancez l'application Ollama ou 'ollama serve'.")

    def _log_exchange(self, messages, answer, duration, raw):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": self.model,
            "duration_s": round(duration, 2),
            "prompt_tokens": raw.get("prompt_eval_count"),
            "completion_tokens": raw.get("eval_count"),
            "messages": messages,
            "answer": answer,
        }
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def is_available(self) -> bool:
        try:
            return self.session.get(self.base_url + "/api/tags", timeout=3).ok
        except requests.RequestException:
            return False