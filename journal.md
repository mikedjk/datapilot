auteur : DJOKOUEHI goba Mike
racine : C:\formation\datapilot

# Etape 0
Je n'avais pas python 3.12 donc j'ai du l'installer, le ".\.venv\Scripts\Activate.ps1" ne s'activait pas donc j'ai fait "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned" technique vu le net et j'ai rélancé puis ça  marché.
tout est bon pour cette étape.

1. LLM local vs service en ligne pour ShopNova

Avantage : la confidentialité. Les questions et les données de ventes (clients, chiffres) ne quittent pas la machine. Il n’y a ni coût à la requête ni compte à créer.
Inconvénient : les performances. Un modèle 7B local est moins puissant qu’un grand modèle en ligne, plus lent, et il demande une machine avec assez de RAM.

2. Pourquoi le premier appel est lent
Au premier appel, Ollama doit charger 4,7 Go du modèle du disque vers la mémoire RAM ou GPU. Ensuite les appels suivants sautent cette étape.

3. Rôle d’un environnement virtuel
Il isole les bibliothèques de ce projet, avec leurs versions, du reste de ton système. Par exemple au debut j'avais python 3.15 et "faiss" ne supportait pas Python 3.15. Avec deux projets qui exigent deux versions différentes de Gradio, une installation globale ne pourrait en garder qu’une, et l’un des deux projets casserait. Avec un .venv par projet, chacun a sa version.

4. Le glossaire des KPI

Il faut compter uniquement les commandes au statut « livrée », avec la formule quantite × prix_unitaire × (1 − remise_pct/100).
exclus : les commandes « annulée », « en cours » et « retournée » (une commande retournée est remboursée), ainsi que les frais de livraison.
Cette information n’est pas dans la base parce que la base stocke des données brutes (lignes, prix, statuts). 


# Etape 1
j'ai eu des diffultés au debut , je pensais tout cette étape se faisait dans le powershell, mais non c'est sur un fichier Py. Apres j'ai mis le code et rempli (voir config).

1. Pourquoi BASE_DIR vient de __file__
__file__ est l’emplacement du fichier config.py, qui ne change jamais. Le dossier courant dépend de l’endroit d’où tu lances la commande. Avec un chemin relatif, lancer le script depuis un autre dossier le ferait chercher la base au mauvais endroit. Avec BASE_DIR, les chemins sont corrects d’où que tu lances (c’est l’expérience à tenter dans ton carnet).

2. Pourquoi int() / float()
os.getenv renvoie toujours une chaîne de caractères. "8192" n’est pas le nombre 8192 : on ne peut pas calculer avec, et un serveur qui attend un nombre dans le JSON refuserait un str. La conversion donne le bon type dès la lecture.

3. Température basse pour du SQL (reponse IA)
Une température basse rend le modèle quasi déterministe : il choisit les tokens les plus probables. Pour du SQL, on veut une syntaxe exacte et le même résultat à chaque fois. À l’inverse, on préfère une température plus élevée pour la créativité : brainstorming, écriture de textes, slogans, variantes de formulations.

4. Quels réglages changeront ou pas (reponse IA)

Souvent modifiés pendant la mise au point : LLM_MODEL (7b ou 3b selon la vitesse), LLM_TEMPERATURE, LLM_TIMEOUT, LLM_NUM_CTX, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, MAX_STEPS, MAX_HISTORY_TURNS. Ce sont les leviers du banc de test de l’étape 14.
Presque jamais : DB_PATH, DOCS_DIR, LOG_DIR, OLLAMA_URL (tant que tu restes en local) et EMBEDDING_MODEL (le changer oblige à re-vectoriser tous les documents, et les résultats de recherche changent).

# Etape 2


j'ai pas eu de soucis, j'ai pu remplir facilement. voici les resultats des expériences : 
- Message system 
{"role": "system", "content": "Tu réponds uniquement en anglais."} :
Code HTTP        : 200
Réponse          : Sure, how can I assist you today?
Tokens lus       : 16
Tokens générés   : 10
Durée            : 5.2 s

- format JSON :
Code HTTP        : 200
Réponse          : {


}
Tokens lus       : 16
Tokens générés   : 3
Durée            : 3.2 s
le format a changé et j'ai l'impression que la durée a baissé

- ollama stoppé :
on obtient "requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=11434): Max retries exceeded ...",La cause réelle est ConnectionRefusedError [WinError 10061] : Python a frappé à la porte du port 11434 et personne n’a répondu.

1. « Je m’appelle Lina », puis « Comment je m’appelle ? »
J’ai envoyé « Je m’appelle Lina. » dans un premier appel, puis « Comment je m’appelle ? » dans un second appel séparé. Le modèle n’a pas pu répondre : il a répondu à côté de la question (« How do I know my name? ») au lieu de dire « Lina ». Chaque requête HTTP est indépendante : le serveur Ollama ne garde aucun état entre deux appels, et le modèle ne voit que les messages contenus dans la requête en cours.
Quand j’ai renvoyé tout l’historique (question, réponse, nouvelle question) dans un seul appel, le modèle a retrouvé le prénom. On en déduit qu’un LLM n’a pas de mémoire propre : la « mémoire » d’un chatbot.

2. L’effet de "format": "json"
Il force le modèle à produire une sortie qui est du JSON valide, sans phrase d’introduction ni balises autour.

3. Pourquoi prompt_eval_count augmente avec un message system
Le message system fait partie du texte envoyé : le modèle doit le lire, donc ses tokens s’ajoutent aux tokens lus. Conséquence pour un system prompt de 1 000 tokens : ces 1 000 tokens sont relus à chaque question (et à chaque étape de l’agent). Cela allonge le temps de réponse, consomme de la fenêtre de contexte et, sur une API payante, coûterait à chaque appel.

4. L’exception quand Ollama est arrêté
on obtient "requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=11434): Max retries exceeded ...",La cause réelle est ConnectionRefusedError [WinError 10061] : Python a frappé à la porte du port 11434 et personne n’a répondu.

# Etape 3
tout est ebon, Point de contrôle 3 validé :
4 tests passés ;
avec Ollama lancé : True OK ;
avec Ollama arrêté : deux avertissements (pauses de 1,0 s puis 2,0 s), puis une LLMError lisible qui se termine par « Lancez l’application Ollama ou ‘ollama serve’ ».

1. Pourquoi ne pas réessayer une erreur 404 ?
Un 404 est une erreur définitive : la ressource demandée n’existe pas, et la renvoyer 3 fois ne la fera pas apparaître. Un retry n’a de sens que pour une panne temporaire (serveur surchargé, redémarrage). Exemple dans notre projet : LLM_MODEL mal écrit (qwen2.5:7bb) ou modèle non téléchargé, comme l’indique le tableau de dépannage de l’annexe C. Réessayer ferait seulement perdre du temps.

2. Combien de secondes de pause au maximum avec max_retries = 3 et backoff_factor = 1 ?
Les pauses ont lieu après les essais 1 et 2, pas après le 3e : 1 × 2⁰ + 1 × 2¹ = 1 + 2 = 3 secondes. Pour le temps d’attente total dans le pire cas, il faut ajouter la durée des tentatives elles-mêmes : jusqu’à timeout secondes chacune. Avec timeout=120, cela fait au pire 3 × 120 + 3 = 363 s, soit environ 6 minutes.

3. Pourquoi expliquer quoi faire (« ollama serve ») ?
L’utilisateur final n’est pas forcément un développeur : une exception technique (NewConnectionError, WinError 10061) ne lui dit rien. Un message avec la cause probable et l’action à faire lui permet de se débloquer seul, sans appeler le support. Notre agent (étape 10) transformera cette LLMError en phrase lisible dans l’interface.

4. Pourquoi JSONL plutôt qu’un gros fichier JSON ?
Un fichier JSON unique est une seule structure : pour y ajouter une entrée, il faut relire et réécrire tout le fichier (ou gérer la virgule et le crochet fermant), et un crash en cours d’écriture le corrompt entièrement. Avec JSONL, ajouter un échange = ajouter une ligne en fin de fichier (mode "a"), sans toucher au reste. On peut aussi le lire ligne par ligne sans tout charger, et un crash n’abîme qu’au pire la dernière ligne. Pandas le lit directement avec read_json(..., lines=True), ce que tu feras à l’étape 11.

5. Précautions en production pour un journal contenant les questions des utilisateurs

Confidentialité : les questions peuvent contenir des données personnelles ou sensibles (noms de clients, chiffres internes). Il faut limiter l’accès au fichier (droits restreints) et éventuellement masquer ou anonymiser certains contenus.
Durée de conservation : ne pas garder indéfiniment, avec une purge ou une rotation automatique (par exemple 30 jours).
Cadre légal (RGPD) : information des utilisateurs, finalité claire (debug et amélioration), droit d’accès et de suppression.
Ne jamais commiter ce fichier dans Git, ce que fait déjà ton .gitignore avec logs/*.jsonl.

# Etape 4

j'au ecrire les TODO avec l'aide de l'IA mais j'ai compris globalement et passé le test donc tout est bon.


1. Pourquoi max_turns * 2 ? Et si la fenêtre commençait par une réponse assistant ?
Un tour contient deux messages (une question user et une réponse assistant), donc N tours = 2 × N messages. Si on gardait un nombre impair, la fenêtre pourrait commencer par une réponse sans sa question : le modèle verrait une réponse « dans le vide », sans savoir à quoi elle répond, ce qui le déroute et dégrade la qualité.

2. Pourquoi le system prompt ne doit-il jamais sortir de la fenêtre ?
C’est lui qui définit le rôle de l’agent, ses outils et le format JSON obligatoire. S’il disparaissait, l’agent oublierait comment répondre : plus de JSON, plus de règles de sécurité (SELECT uniquement, pas d’email client). C’est pourquoi il est ajouté séparément, en dehors de la découpe de l’historique.

3. Fenêtre glissante, budget de tokens, résumé : laquelle pour un assistant de rédaction d’un rapport de 30 pages ?

Fenêtre glissante : simple et prévisible, mais elle oublie tout ce qui est ancien (les consignes du début, la structure du rapport).
Budget de tokens : plus précis, car on remplit la fenêtre jusqu’à une limite réelle en tokens, mais ça oublie aussi le début.
Résumé des anciens échanges : on condense le passé en quelques lignes et on garde le récent en entier. Ça coûte un appel LLM supplémentaire et le résumé peut perdre des détails.

Pour un rapport de 30 pages, je choisirais le résumé (éventuellement combiné avec un budget de tokens) : il faut conserver la structure, les décisions et le ton des parties déjà écrites, ce qu’une fenêtre glissante simple perdrait.

4. Quand « caractères / 4 » se trompe-t-il beaucoup ?
Le ratio dépend de la langue et du contenu. Le français avec accents, le code, les nombres, les tableaux markdown ou les langues non latines (chinois, arabe) se découpent en beaucoup plus de tokens par caractère. Par exemple, un long tableau de chiffres SQL peut contenir bien plus de tokens que longueur // 4 ne le suggère. Pour un chiffre fiable, il faut lire prompt_eval_count renvoyé par Ollama (ce que tu as vu à l’étape 2).

# Etape 5

# Etape 5
Difficultés : j'avais collé mon code de test dans prompts.py (et nommé un fichier
"import sqlite3.py"), ce qui relançait des appels au LLM à chaque import.
Solution : prompts.py ne contient que le template et build_system_prompt ; le test est
dans explorer/test_prompt.py. Premier test : timeout de 120 s, le modèle devait se charger
et lire un prompt d'environ 2 200 tokens.
Point de contrôle 5 validé : 3 JSON valides (query_database, search_docs, final_answer).
Prompt : 8 882 caractères, environ 2 220 tokens.
Modifications du prompt : aucune après le premier essai.

1. Pourquoi du JSON plutôt que des phrases ? Que faire de « Je pense qu’il faudrait regarder dans la base » ?
Un programme ne peut pas deviner une intention dans une phrase libre. Avec du JSON, action et input se lisent avec json.loads, sans ambiguïté. Une réponse comme « Je pense qu’il faudrait regarder… » n’est pas du JSON : parse_llm_output lève une ParseError. route_query la transforme alors en message d’erreur renvoyé au LLM, du type « réponds uniquement avec le JSON ». Le modèle peut ainsi se corriger, sans que le programme plante.

2. À quoi sert thought ?
Pour le modèle, écrire son raisonnement avant l’action l’aide à mieux choisir (il « réfléchit à voix haute »). Pour moi, c’est un outil de débogage : dans les journaux, je vois pourquoi il a choisi tel outil et je repère où le raisonnement part de travers.

3. Pourquoi insérer le schéma avec {schema} ?
Le schéma est lu directement dans la base par get_schema(). Il est donc toujours exact : si la base change, le prompt suit sans retouche. Le recopier à la main risquerait des fautes de frappe (une colonne mal orthographiée fait inventer de mauvaises requêtes) ou un schéma périmé.

4. Quels pièges dans les rappels, et quelle erreur sans eux ?

Accents des statuts : sans le rappel, le modèle écrit 'livree' et obtient 0 ligne.
Dates en texte ISO : il utiliserait YEAR() (qui n’existe pas en SQLite) ou une comparaison fausse.
Pas de colonne « montant » : il inventerait commandes.montant et ferait une erreur SQL. Il faut calculer quantite × prix_unitaire × (1 − remise/100).
CA = commandes livrées seulement, sans frais de livraison : il inclurait les commandes annulées, retournées ou en cours, ce qui gonflerait le CA.
Panier moyen avec COUNT(DISTINCT commande_id) : il diviserait par le nombre de lignes, et la jointure créerait des doublons.
Pas d’email, SELECT uniquement : il pourrait afficher des emails ou accepter une demande de suppression.

5. Pourquoi ne pas mettre « Combien de clients VIP avons-nous ? » dans les exemples ?
Si la question et sa réponse figurent mot pour mot dans le prompt, le modèle les recopie sans raisonner. Le banc de test (étape 14) affichera alors 100 % sur cette question, alors qu’il mesure de la mémorisation et non de la compétence. Le score est trompeur. Il faut donc des exemples différents des questions d’évaluation (c’est pourquoi j’ai pris les canaux et le taux d’annulation).

6. Le system prompt est-il une garantie ? Que fait le code s’il n’est pas respecté ?
Non, c’est une consigne, pas une règle imposée : un petit modèle 7B peut l’ignorer (texte autour du JSON, mauvaise clé, outil inventé), et un utilisateur malveillant peut tenter une prompt injection. Le code doit donc se protéger lui-même :

un parseur tolérant, avec renvoi d’un message d’erreur au LLM ;
un routing qui refuse les outils inconnus ;
une base ouverte en lecture seule avec validation du SQL ;
une limite du nombre d’étapes.