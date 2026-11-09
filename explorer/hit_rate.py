"""explorer/hit_rate.py — Mesure du hit rate @1 et @3 de la recherche documentaire."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pour importer config et tools

import config
from tools import DocSearchTool, load_corpus, load_embedder

JEU_EVAL = [
    ("Combien de jours pour retourner un article ?", "02_politique_retours.md"),
    ("Comment est défini le chiffre d'affaires ?", "01_glossaire_kpi.md"),
    ("Quels sont les critères pour devenir VIP ?", "03_segmentation_clients.md"),
    ("Quelles colonnes contient la table lignes_commande ?", "04_dictionnaire_donnees.md"),
    ("À partir de quel montant la livraison est-elle gratuite ?", "05_livraison.md"),
    ("Peut-on afficher l'email d'un client dans un rapport ?", "06_regles_reporting.md"),
    ("Qu'est-ce qu'un client actif ?", "01_glossaire_kpi.md"),
    ("Les produits de beauté peuvent-ils être retournés ?", "02_politique_retours.md"),
]


def hit_rate(outil: DocSearchTool, k: int) -> float:
    """Part des questions dont le bon document figure parmi les k premiers résultats."""
    hits = 0
    for question, source_attendue in JEU_EVAL:
        sources = [chunk.source for _, chunk in outil.search(question, k=k)]
        if source_attendue in sources:
            hits += 1
    return hits / len(JEU_EVAL)


if __name__ == "__main__":
    chunks = load_corpus(config.DOCS_DIR, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    outil = DocSearchTool(chunks, load_embedder(config.EMBEDDING_MODEL), top_k=config.TOP_K)
    print(f"{len(chunks)} morceaux (chunk_size={config.CHUNK_SIZE}, overlap={config.CHUNK_OVERLAP})")
    for k in (1, 3):
        print(f"Hit rate @{k} : {hit_rate(outil, k):.0%}")