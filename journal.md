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

# Etape 6
Pas de difficultés
1. Quelle barrière garder si on n’en gardait qu’une ?
La lecture seule (barrière 1, mode=ro + PRAGMA query_only). C’est le moteur de base de données lui-même qui refuse toute écriture, quoi que le LLM écrive : on ne dépend pas d’une analyse de texte que quelqu’un pourrait contourner. Les autres restent utiles :

la validation donne un message clair au LLM avant exécution, pour qu’il se corrige ;
les paramètres ? empêchent qu’une valeur saisie change le sens de la requête (même en lecture seule, OR '1'='1' ferait fuiter des données) ;
la limite de lignes protège la mémoire et la fenêtre de contexte du LLM.

2. Pourquoi la f-string renvoie 500 clients ?
Le texte VIP' OR '1'='1 est collé dans la requête, qui devient WHERE segment = 'VIP' OR '1'='1'. La condition '1'='1' est toujours vraie, donc toutes les lignes sont retenues (39 + 90 + 371 = 500). La saisie a changé la structure de la requête. Avec ?, la saisie est traitée comme une simple valeur : on cherche un segment nommé littéralement « VIP’ OR ‘1’='1 », il n’y en a aucun, donc 0.

3. Pourquoi run ne doit jamais lever d’exception ? (reponse IA)
Une exception non gérée interromprait l’agent et ferait planter l’interface. Le message d’erreur est destiné au LLM : au tour suivant, il lit ERREUR SQL : no such column: montant, comprend son erreur et réécrit sa requête. C’est le mécanisme d’auto-correction de l’agent.

4. Un exemple de requête légitime refusée par la liste de mots interdits
SELECT REPLACE(nom, 'é', 'e') FROM clients est refusée à cause de REPLACE, alors que c’est ici une fonction de texte inoffensive. De même, un filtre sur une valeur contenant un mot interdit (WHERE motif = 'update') serait bloqué. La liste est donc volontairement prudente : elle refuse parfois à tort, mais la lecture seule reste la vraie protection.

5. Pourquoi un tableau markdown plutôt qu’un print de liste de tuples ?
Le LLM lit du texte : le tableau lui donne les noms de colonnes à côté des valeurs, un format qu’il connaît très bien, et il est lisible aussi par l’utilisateur. Une liste de tuples comme [('VIP', 39)] perd les noms de colonnes et mélange la syntaxe Python avec les données. On y ajoute le nombre de lignes et une mention de troncature, pour que le modèle sache si le résultat est complet.

6. Protection supplémentaire sur PostgreSQL en production (reponse IA)
Un rôle de base de données dédié en lecture seule : GRANT SELECT uniquement sur les tables (ou vues) nécessaires, sans accès aux colonnes sensibles comme l’email. On ajoute un statement_timeout, une connexion à un réplica en lecture et la journalisation (pgaudit). La protection est alors appliquée côté serveur, quelle que soit l’application.

# Etape 7 
(totalement avec l'IA ), je n'ai pas compris cette partie, manque de temps j'avance avec l'IA
points à comprendre :
chunk_text remplit un morceau mot par mot ; quand le mot suivant ne rentre plus, on enregistre le morceau et on repart de ses overlap derniers caractères, sans le premier mot (qui peut être coupé).
La condition not current accepte un mot plus long que chunk_size : sans elle, un mot géant provoquerait une boucle infinie.
chunk_markdown découpe d’abord par titres ## (la structure du document), puis par taille. Le préfixe est ajouté après le découpage, donc un morceau peut dépasser chunk_size de la longueur du préfixe : c’est normal.
load_corpus trie les fichiers (sorted) pour un ordre stable, et lit en UTF-8, indispensable sous Windows.

1. Tailles de 200, 500 et 1 000 caractères
Mes mesures sur ton corpus : 69 morceaux à 200, 36 à 500, 35 à 1 000. Refais-le chez toi (load_corpus('data/docs', chunk_size=200, overlap=40)) et lis quelques morceaux. À 200 caractères, une règle est souvent coupée en plein milieu : le préfixe [Titre — Section] aide, mais le morceau perd des conditions ou des exceptions. De 500 à 1 000, le nombre de morceaux change peu, car les sections du corpus sont courtes.

2. Pourquoi le préfixe améliore la recherche
Un morceau comme « Ce délai est porté à 60 jours pour les clients du segment VIP » ne dit pas de quel délai il s’agit. Avec [Politique de retours et de remboursement — ShopNova — Délai de rétractation] devant, son vecteur se rapproche d’une question sur le « délai de retour ». Le morceau est compréhensible tout seul, et l’agent peut en plus citer la source.

3. Sans chevauchement, si une règle est coupée en deux
Aucun des deux morceaux ne contient la règle entière : la recherche en ramène une moitié, et le LLM répond avec une information incomplète. Par exemple, il lirait « 30 jours » sans l’exception « 60 jours pour les VIP ». Le chevauchement garantit qu’une idée coupée à la frontière apparaît entière dans au moins un des deux morceaux.

4. Pourquoi encoding="utf-8" sous Windows
Sans précision, Python utilise l’encodage par défaut du système, souvent cp1252 sous Windows. Les documents contiennent des accents, des guillemets « » et des tirets longs « — » : ils seraient mal lus (Ã© au lieu de é) ou provoqueraient une UnicodeDecodeError. Le texte corrompu serait ensuite vectorisé tel quel et fausserait la recherche.

5. Découper un PDF de 80 pages sans titres
On extrait le texte, puis on découpe par paragraphes (lignes vides), qu’on regroupe jusqu’à la taille voulue, avec chevauchement. On peut aussi découper par phrases, ou détecter des titres d’après la taille de police. On garde le numéro de page dans les métadonnées pour citer la source, et on vérifie que les tableaux et les en-têtes répétés à chaque page n’ont pas pollué le texte.

# Etape 8

Ce que j'ai retenu :
Un embedding est une liste de 384 nombres qui représente le sens d’un texte. Deux phrases de même sens ont des vecteurs proches, même sans mot en commun (« renvoyer un article » ≈ « délai de rétractation »).
La similarité cosinus mesure si deux vecteurs pointent dans la même direction (1 = même sens). Avec des vecteurs normalisés (longueur 1), c’est simplement le produit scalaire, ce que calcule faiss.IndexFlatIP.
FAISS range les vecteurs et retrouve les k plus proches. Il ne stocke pas les textes : on garde la liste chunks, alignée sur les positions de l’index.

1. Pourquoi le même modèle pour la question et les documents ?
Chaque modèle a son propre « espace » de vecteurs (dimension, géométrie). Comparer un vecteur de question issu d’un modèle A à des vecteurs de documents issus d’un modèle B n’a aucun sens : les distances ne signifient plus rien.

2. Pourquoi normaliser pour un IndexFlatIP ?
Le produit scalaire dépend à la fois de la direction et de la longueur des vecteurs. Sans normalisation, un vecteur long obtiendrait de grands scores sans être plus proche en sens. Normalisé, le produit scalaire vaut exactement le cosinus, qui ne mesure que la direction.

3. La recherche renvoie toujours k passages, même pour « salaire moyen des employés » : quel risque ?
L’agent reçoit trois passages hors sujet et peut en tirer une réponse inventée en croyant qu’ils répondent à la question (regarde le passage 3 de ta propre sortie : score 0,61, il parle du remboursement, pas du délai). Deux parades : un seuil de score en dessous duquel on ne renvoie rien (le « Pour aller plus loin » du guide), et une consigne dans le prompt disant de répondre « l’information n’existe pas » si les passages ne répondent pas à la question.

4. Hit rate à 300, 500, 800 : que conclure ? 8 questions suffisent-elles ?
Teste-le chez toi avec CHUNK_SIZE modifié, en relançant hit_rate.py. À 100 % sur 500, tu ne verras probablement aucune différence. Huit questions ne suffisent pas pour conclure : chaque question pèse 12,5 points, les questions sont faciles (elles reprennent presque les titres des sections), et elles sont toutes bien formulées. Il faut un jeu plus large, avec des reformulations, des questions à cheval sur plusieurs documents et des questions hors périmètre.

5. Pourquoi le RAG plutôt que le fine-tuning, et plutôt que tout coller dans le prompt ?

Face au fine-tuning : une politique qui change chaque année se met à jour en modifiant un document et en ré-indexant en quelques secondes, alors que le fine-tuning demande de réentraîner, coûte cher et ne permet pas de citer la source.
Face au prompt géant : la fenêtre de contexte est limitée, chaque appel relirait toute la documentation (lent en local, coûteux sur une API), et beaucoup de texte inutile noie l’information utile. Cela ne passerait pas à l’échelle avec des centaines de documents.

6. Une solution qui stocke aussi les textes et les métadonnées ?
Par exemple Chroma, Qdrant ou pgvector (extension PostgreSQL). On les préfère à FAISS quand il y a beaucoup de documents, des filtres sur les métadonnées (date, source, droits d’accès), des mises à jour ou suppressions fréquentes, de la persistance, ou plusieurs utilisateurs, car FAISS ici est reconstruit en mémoire à chaque démarrage.

# Etape 9

1. Pourquoi \{.*\} doit-il être gourmand ?
Un JSON peut contenir des objets imbriqués, par exemple params. Avec .*? (paresseux), la regex s’arrête au premier } et coupe l’objet en plein milieu. Je l’ai vérifié sur {"action": "query_database", "params": {"a": 1}, "input": "SELECT 1"} :

gourmand : le JSON complet est récupéré ;
paresseux : on obtient {"action": "query_database", "params": {"a": 1}, donc json.loads échoue.

Le gourmand va du premier { au dernier }. Sa limite : si le LLM écrit deux objets JSON dans la même réponse, ils seront fusionnés en un texte invalide. Dans ce cas, ParseError renvoie un message d’erreur au LLM, qui peut se corriger.

2. Pourquoi renvoyer un RouteResult d’erreur plutôt que lever une exception ?
Le destinataire du message est le LLM, pas le programme. La boucle de l’étape 10 renvoie ce message au modèle sous la forme « ERREUR DE FORMAT : … », et il peut alors corriger son outil ou son JSON. Une exception arrêterait l’agent et ferait planter l’interface. C’est le même principe que pour SQLTool.run à l’étape 6.

3. Que modifier pour ajouter un troisième outil ?
Trois endroits seulement :

créer la classe de l’outil dans tools.py, avec name, description et run(texte) -> str ;
l’ajouter au dictionnaire tools dans build_agent() ;
le décrire dans le system prompt de prompts.py : nom, quand l’utiliser, ce que contient input.

route_query ne change pas, car il cherche simplement decision.action dans le dictionnaire. C’est l’avantage du routing par dictionnaire.

4. Avantage de « n’importe quel objet qui a une méthode run » pour les tests ?
On peut remplacer les vrais outils par des doublons (fakes) : sans base, sans FAISS, sans téléchargement de modèle. Les tests sont rapides et toujours identiques (8 tests en 0,11 s). Le guide l’illustre avec FakeLLM à l’étape 11.

5. Tool calling natif contre version manuelle ?

Le natif apporte : un format de sortie garanti par l’API, avec des schémas typés pour les arguments. Il y a moins de parsing défensif et moins d’erreurs de JSON, surtout avec un petit modèle.
la version manuelle t’a fait comprendre : que le LLM ne fait que proposer du texte et que c’est Python qui exécute. Elle a aussi montré les modes d’échec concrets (JSON mal formé, outil inventé, clé action_input à la place de input) et pourquoi un parseur tolérant et des messages d’erreur sont nécessaires. C’est ce qui garantit que la base ne peut pas être modifiée par le modèle.

# Etape 10

J'ai eu des difficultés à comprendre le code de cette étape (la boucle de l'agent,
la différence entre le brouillon et la mémoire, et la construction de build_agent).
Je me suis fait aider par l'IA pour écrire le code, puis je me suis fait expliquer
chaque partie pour la comprendre.

Ce que j'ai retenu : la méthode ask() répète une boucle. Le LLM propose une action
en JSON, route_query l'exécute, puis le résultat est renvoyé au LLM sous la forme
« OBSERVATION (outil) : ... ». Cela continue jusqu'à la réponse finale ou jusqu'à
la limite d'étapes. Seule la réponse finale est gardée en mémoire longue.

Point de contrôle 10 : [5 tests passés / résultat obtenu].
- Clients VIP : outils [39], (référence : 39)
- CA net 2025 : outils [166 091,86 €],(référence : 166 091,86 €)
- Délai de retour VIP : outils [60 jours], (référence : 60 jours)
- Panier moyen 2025 : outils [115,99],(référence : 115,99 €)
- Clients actifs puis « et combien sont VIP ? » : outils [498],(référence : 445)

1. Pourquoi limiter le nombre d'étapes ?
Sans limite, si le LLM répète la même requête erronée, l'agent tournerait sans fin.
Chaque tour prend plusieurs secondes en local et le brouillon grossit à chaque
étape, jusqu'à saturer la fenêtre de contexte. Avec max_steps, l'agent s'arrête
toujours : il force alors une réponse finale avec les informations déjà obtenues,
ou dit clairement qu'il n'a pas réussi.

2. Différence entre la mémoire longue et le brouillon
La mémoire longue (Conversation) garde seulement les questions de l'utilisateur et
les réponses finales, d'une question à l'autre. Le brouillon (scratchpad) contient
les décisions du LLM et les observations d'une seule question, puis il est jeté.
Si toutes les observations restaient en mémoire, un tableau SQL de 50 lignes
remplirait vite la fenêtre de contexte : les appels deviendraient plus lents, le
system prompt serait noyé et les anciens échanges sortiraient de la fenêtre.

3. Pourquoi l'observation est envoyée avec le rôle user
Le rôle assistant est réservé à ce que le modèle a lui-même écrit : y mettre un
résultat d'outil lui ferait croire qu'il l'a dit. Le rôle system sert aux consignes
permanentes placées en tête de conversation. Un résultat d'outil est une
information qui vient de l'extérieur, comme une réponse à sa demande, donc le
rôle user. Les API de tool calling natif ont un rôle « tool » dédié pour cela.

4. Panier moyen : la documentation a-t-elle été consultée avant le SQL ?
 Oui, l’agent a appelé search_docs d’abord (passage « Panier moyen » du glossaire),
  puis query_database. Aucune modification de prompt n’était nécessaire

5. Comment l'agent comprend « eux » dans « Et combien d'entre eux sont VIP ? »
C'est la mémoire longue : la question précédente et sa réponse (445 clients actifs)
sont renvoyées au LLM à chaque appel, il peut donc relier « eux » aux clients
actifs.

6. Que prouvent les tests avec un faux LLM, et que ne prouvent-ils pas ?
Ils prouvent la mécanique : la boucle, l'ajout de l'observation au brouillon, la
limite max_steps, l'auto-correction après une erreur de format, la mémoire entre
deux questions et le message lisible quand le LLM est indisponible. Ils ne
prouvent pas que le vrai modèle choisira le bon outil, écrira le bon SQL ou
donnera le bon chiffre : le faux LLM répète des réponses écrites à l'avance. Il
faut pour cela l'évaluation avec le vrai modèle (étape 14).

Erreurs rencontrées. « 498 clients actifs au lieu de 445 : l’agent n’a pas consulté la documentation et a ignoré les critères livrée et 365 jours. Cause : la règle « search_docs avant le SQL » n’a pas été appliquée à « client actif ». »


# Etape 11

Point de contrôle 11 : 41 tests passés (étapes 3 à 10).

Journaux (14 appels de l'agent, hors les 2 tests « Réponds juste OK » de l'étape 3) :
- durée moyenne d'un appel : 59 s (médiane 40 s ; minimum 16 s ; maximum 223 s, le
  premier appel, qui charge le modèle)
- tokens lus : environ 2 880 par appel (de 2 507 à 3 419)
- tokens générés : environ 85 par appel

Analyse d'une erreur : à la question « Combien de clients actifs au 31 décembre
2025 ? », l'agent a répondu 498 au lieu de 445. L'erreur s'est produite dès la
première décision du LLM : il a écrit directement une requête SQL, sans appeler
search_docs, alors que mon prompt demande de consulter la documentation avant tout
indicateur défini. Sa requête comptait tous les clients ayant passé au moins une
commande, quel que soit le statut, sans filtrer sur « livrée » ni sur les 365 jours
précédant le 31/12/2025. La définition du glossaire n'a donc pas été appliquée.
De plus, la réponse finale a mélangé le panier moyen de la question précédente avec
les nouveaux chiffres : le modèle a recopié des éléments de la mémoire.

1. Pourquoi un test qui utiliserait le vrai LLM serait-il « instable » ?
Le modèle n'est pas déterministe : même avec une température basse, la même
question peut donner une formulation ou un SQL différents d'un lancement à l'autre.
Le test dépendrait aussi d'Ollama (démarré ? modèle chargé ?) et durerait de 20 s à
plusieurs minutes. Un test doit être rapide et toujours donner le même résultat,
sinon un échec ne dit plus si le code est cassé ou si le modèle a simplement varié.

2. Pourquoi prompt_tokens augmente-t-il au fil des étapes d'une même question ?
À chaque étape, tout le brouillon est renvoyé au LLM : le system prompt, l'historique,
puis chaque décision du LLM et chaque observation reçue. Chaque étape ajoute donc du
texte. Par exemple, pour le panier moyen, les tokens lus sont passés de 2 653 à
3 120, puis à 3 419.

3. Durée moyenne d'un appel sur mon poste, et conséquence pour l'interface
En moyenne 59 s par appel sur mon poste (environ 32 s sans le premier chargement du
modèle). Une question à trois étapes demande donc de 1 min 30 à 3 min d'attente.
L'interface doit afficher la question tout de suite et montrer un indicateur de
chargement, sinon l'utilisateur croit que l'application est bloquée. Afficher les
étapes (requête SQL, documents consultés) aide aussi à patienter.

4. Un test unitaire vert garantit-il que l'agent donnera le bon chiffre d'affaires ?
Non. Les tests avec un faux LLM prouvent la mécanique (routing, boucle, mémoire,
limite d'étapes, gestion des erreurs), mais le faux LLM répond ce qu'on lui a
écrit à l'avance. Ils ne disent rien sur le choix des outils ni sur le SQL du vrai
modèle. Preuve concrète : les 41 tests étaient verts alors que l'agent a répondu 498
clients actifs au lieu de 445. Seule l'évaluation avec le vrai LLM sur des questions
de référence (étape 14) mesure la justesse des réponses.

# Etape 12

# Etape 12

ui.py écrit avec l'aide de l'IA, puis expliqué : message_text recolle le texte quand
Gradio 6 renvoie une liste, steps_to_messages transforme les étapes de l'agent en
blocs repliables, et create_ui enchaîne deux événements.
Point de contrôle 12 : 3 tests passés ; interface ouverte sur http://127.0.0.1:7860 :
la question s'affiche tout de suite, un indicateur tourne, la réponse arrive précédée
d'un bloc repliable « 🔧 Requête SQL » ou « 🔧 Recherche documentaire ».
Exemples testés : chiffre d'affaires net 2025 (166 091,86 €) et délai de retour VIP
(60 jours).
J'ai ajouté un pytest.ini (testpaths = tests) car pytest -q plantait en lisant mes
scripts d'exploration (explorer/test_prompt.py appelle le LLM, et test_agent.py
existait en double).

1. Pourquoi deux événements enchaînés ?
Avec une seule fonction, la question n'apparaîtrait qu'à la fin du calcul, donc après
une ou plusieurs minutes. Le premier événement est instantané : il affiche la question
et vide la saisie. Le second est lent : il appelle l'agent pendant que Gradio montre
un indicateur de chargement. L'utilisateur voit tout de suite que sa demande est
prise en compte.

2. Quels fichiers modifier pour changer d'interface, ou de LLM ?
Pour remplacer Gradio par Streamlit ou une application mobile : seulement ui.py (et
son lancement), car l'agent ne connaît que ask() et reset(). Pour remplacer Ollama par
une API en ligne : seulement llm_client.py (et les réglages dans config.py), car
l'agent ne connaît que chat(messages, json_mode).

3. Pourquoi montrer la requête SQL à un utilisateur métier ?
Pour la confiance et la vérification : il voit d'où vient le chiffre (quelle table,
quels filtres, quelle période). Un collègue qui connaît le SQL peut repérer une erreur,
comme le 498 clients actifs de l'étape 10. Les blocs sont repliables : ils ne gênent
pas ceux qui ne veulent que la réponse.

4. Deux onglets, que constate-t-on sur la mémoire ?
Ce que j'ai observé : dans l'onglet 2, l'agent a compris « eux » alors que je n'y avais
pas posé la première question.
Il n'existe qu'un seul objet Agent, créé au lancement de ui.py : tous les onglets
partagent donc la même mémoire, et « Réinitialiser » vide la mémoire de tout le monde.
En production, deux utilisateurs verraient leurs conversations se mélanger, et les
informations de l'un pourraient apparaître dans les réponses de l'autre (problème de
confidentialité). Il faudrait une conversation par session (par exemple un état Gradio
par utilisateur).

5. Que se passe-t-il si j'arrête Ollama ?
L'interface ne plante pas. Elle affiche dans le chat : « Le moteur LLM est
indisponible. Lancez l'application Ollama ou 'ollama serve', puis réessayez. »
C'est acceptable pour un utilisateur : le message donne la cause et l'action à faire,
sans jargon technique. Il manque un bouton pour réessayer sans retaper la question, et
ce message d'erreur est enregistré dans la mémoire de la conversation comme une vraie
réponse (point à améliorer).