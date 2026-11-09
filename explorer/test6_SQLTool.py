from tools import SQLTool
t = SQLTool("data/ecommerce.db")
print(t.run("SELECT segment, COUNT(*) AS nb FROM clients GROUP BY segment"))
print(t.run("DELETE FROM clients"))
print(t.run("SELECT montant FROM commandes"))