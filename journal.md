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