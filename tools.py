"""tools.py — Les outils de l'agent : SQL (partie 1) et recherche documentaire (parties 2 et 3)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

# Mots-clés qui modifient la base ou son fonctionnement : refusés avant exécution.
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


class SQLValidationError(ValueError):
    """Requête refusée avant exécution."""


def validate_sql(sql: str) -> str:
    """Nettoie la requête et la refuse si elle n'est pas un unique SELECT / WITH."""
    # 1. retirer les balises de code markdown (```sql ... ```), puis les espaces et le « ; » final
    cleaned = re.sub(r"^```(?:sql)?|```$", "", sql.strip(), flags=re.IGNORECASE).strip()
    cleaned = cleaned.rstrip(";").strip()

    # 2. les quatre refus
    if not cleaned:
        raise SQLValidationError("la requête est vide.")
    if ";" in cleaned:
        raise SQLValidationError("une seule requête à la fois est autorisée (pas de « ; » multiple).")
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise SQLValidationError("seules les requêtes SELECT (ou WITH ... SELECT) sont autorisées.")
    interdit = FORBIDDEN.search(cleaned)
    if interdit:
        raise SQLValidationError(f"mot-clé interdit : {interdit.group(1).upper()}.")
    return cleaned


def _cell(value) -> str:
    """Met une valeur en forme pour le tableau : None -> NULL, float -> 2 décimales."""
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def format_results(columns: list[str], rows: list[tuple], truncated: bool = False) -> str:
    """Résultat SQL -> tableau markdown lisible par le LLM."""
    if not rows:
        return "La requête s'est exécutée correctement mais a renvoyé aucun résultat (0 ligne)."

    lignes = [
        f"{len(rows)} ligne(s) :",
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in rows:
        lignes.append("| " + " | ".join(_cell(v) for v in row) + " |")
    if truncated:
        lignes.append(f"(résultat tronqué : seules les {len(rows)} premières lignes sont affichées)")
    return "\n".join(lignes)


class SQLTool:
    name = "query_database"
    description = "Exécute UNE requête SQL SELECT (SQLite) sur la base e-commerce."

    def __init__(self, db_path, max_rows: int = 50) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Base introuvable : {self.db_path}. Lancez d'abord : python data/create_db.py"
            )
        self.max_rows = max_rows

    def _connect(self) -> sqlite3.Connection:
        """Connexion en LECTURE SEULE (barrière n°1)."""
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("PRAGMA query_only = ON")
        return conn

    def run(self, sql: str, params=()) -> str:
        """Exécute la requête. Ne lève JAMAIS d'exception : renvoie du texte pour le LLM."""
        # Barrière n°2 : validation
        try:
            sql = validate_sql(sql)
        except SQLValidationError as exc:
            return f"ERREUR : requête refusée — {exc}"

        # Barrières n°3 (paramètres ?) et n°4 (limite de lignes)
        conn = None
        try:
            conn = self._connect()
            cursor = conn.execute(sql, params)
            colonnes = [d[0] for d in cursor.description]
            lignes = cursor.fetchmany(self.max_rows + 1)
        except sqlite3.Error as exc:
            return f"ERREUR SQL : {exc}. Corrigez la requête et réessayez."
        finally:
            if conn is not None:
                conn.close()

        truncated = len(lignes) > self.max_rows
        return format_results(colonnes, lignes[: self.max_rows], truncated=truncated)

    def get_schema(self) -> str:
        """Instructions CREATE TABLE de la base (insérées dans le system prompt)."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL"
            ).fetchall()
        finally:
            conn.close()
        return "\n\n".join(r[0] for r in rows)
