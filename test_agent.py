from agent import route_query
from tools import SQLTool
outils = {"query_database": SQLTool("data/ecommerce.db")}
print(route_query('{"action": "query_database", "input": "SELECT COUNT(*) AS n\nFROM produits"}', outils))
print(route_query('Voici ma réponse : {"action": "envoyer_email", "input": "x"}',
outils).content)