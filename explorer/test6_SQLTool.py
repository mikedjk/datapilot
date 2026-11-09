import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pour importer tools

from tools import SQLTool

t = SQLTool("data/ecommerce.db")
print(t.run("SELECT segment, COUNT(*) AS nb FROM clients GROUP BY segment"))
print(t.run("DELETE FROM clients"))
print(t.run("SELECT montant FROM commandes"))

import sqlite3
conn = sqlite3.connect("data/ecommerce.db")
saisie = "VIP' OR '1'='1"
print(conn.execute(f"SELECT COUNT(*) FROM clients WHERE segment = '{saisie}'").fetchone())
print(conn.execute("SELECT COUNT(*) FROM clients WHERE segment = ?", (saisie,)).fetchone())