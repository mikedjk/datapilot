"""tools.py — Les outils de l'agent : SQL (partie 1) et recherche documentaire (parties 2 et 3)."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
import numpy as np

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

# ---------------------------------------------------------------------------
# Partie 2 : découpage de la documentation (RAG, indexation)
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    text: str
    source: str   # nom du fichier d'origine
    section: str  # titre de la section « ## »


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Découpe un texte en morceaux d'au plus chunk_size caractères, sans couper les mots,
    chaque morceau reprenant la fin du précédent (chevauchement)."""
    if overlap >= chunk_size:
        raise ValueError("overlap doit être strictement inférieur à chunk_size")

    words = text.split()
    chunks: list[str] = []
    current = ""
    only_overlap = False  # True si current ne contient que le chevauchement repris
    i = 0
    while i < len(words):
        candidate = f"{current} {words[i]}" if current else words[i]
        if not current or len(candidate) <= chunk_size:
            current = candidate
            only_overlap = False
            i += 1
        elif only_overlap:
            current = ""  # le mot ne rentre même pas avec le chevauchement : on l'abandonne
            only_overlap = False
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            # le premier mot de la fin peut être coupé : on le retire
            current = tail.split(" ", 1)[1] if " " in tail else ""
            only_overlap = bool(current)
    if current and not only_overlap:
        chunks.append(current)
    return chunks


def chunk_markdown(text: str, source: str, chunk_size: int = 500, overlap: int = 100) -> list[Chunk]:
    """Découpe un document markdown par section « ## », puis par taille.
    Chaque morceau est préfixé par [Titre du document — Titre de section]."""
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source

    chunks: list[Chunk] = []
    for index, part in enumerate(re.split(r"^##\s+", text, flags=re.MULTILINE)):
        if index == 0:
            # introduction : on retire la ligne « # Titre »
            section = "Introduction"
            content = re.sub(r"^#\s+.+$", "", part, count=1, flags=re.MULTILINE).strip()
        else:
            head, _, rest = part.partition("\n")
            section = head.strip()
            content = rest.strip()
        if not content:
            continue
        for piece in chunk_text(content, chunk_size, overlap):
            chunks.append(Chunk(text=f"[{title} — {section}] {piece}", source=source, section=section))
    return chunks


def load_corpus(docs_dir, chunk_size: int = 500, overlap: int = 100) -> list[Chunk]:
    """Charge tous les fichiers *.md du dossier et renvoie tous leurs morceaux."""
    files = sorted(Path(docs_dir).glob("*.md"))
    if not files:
        raise FileNotFoundError(f"Aucun document .md trouvé dans {docs_dir}")
    chunks: list[Chunk] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(text, path.name, chunk_size, overlap))
    return chunks


# ---------------------------------------------------------------------------
# Partie 3 : embeddings, FAISS et recherche documentaire
# ---------------------------------------------------------------------------

class DocSearchTool:
    name = "search_docs"
    description = (
        "Recherche dans la documentation métier "
        "(KPI, retours, segmentation, données, livraison, reporting)."
    )

    def __init__(self, chunks: list[Chunk], embedder, top_k: int = 3) -> None:
        import faiss  # import local : l'outil SQL reste utilisable sans FAISS

        self.chunks = chunks
        self.embedder = embedder
        self.top_k = top_k
        vectors = self._embed([c.text for c in chunks])
        # IndexFlatIP = produit scalaire ; avec des vecteurs normalisés, c'est le cosinus
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def _embed(self, texts: list[str]) -> np.ndarray:
        vectors = self.embedder.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return np.asarray(vectors, dtype="float32")

    def search(self, query: str, k: int | None = None) -> list[tuple[float, Chunk]]:
        """Les k morceaux les plus proches de la question, du plus proche au moins proche."""
        k = min(k or self.top_k, len(self.chunks))
        query_vector = self._embed([query])  # liste d'UNE question -> matrice (1, dim)
        scores, ids = self.index.search(query_vector, k)
        return [
            (float(score), self.chunks[i])
            for score, i in zip(scores[0], ids[0])
            if i != -1  # FAISS renvoie -1 quand il manque des résultats
        ]

    def run(self, query: str) -> str:
        """Résultats formatés en texte pour le LLM, avec la source de chaque passage."""
        results = self.search(query)
        if not results:
            return "Aucun passage pertinent trouvé dans la documentation."
        blocs = []
        for rang, (score, chunk) in enumerate(results, start=1):
            blocs.append(
                f"[Passage {rang} — source : {chunk.source}, "
                f"section « {chunk.section} », score {score:.2f}]\n{chunk.text}"
            )
        return "\n\n".join(blocs)


def load_embedder(model_name: str):
    """Charge le modèle d'embedding (import local : le téléchargement n'a lieu qu'ici)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)