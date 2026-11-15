# Memoriae

Plateforme expérimentale consacrée à l'étude de la mémoire humaine et à sa modélisation
computationnelle. Memoriae publie des expériences reproductibles, recueille des réponses
pseudonymes et permet d'étudier l'indiçage, les erreurs et la difficulté.

## Architecture

```text
app/auth/         sessions chercheur sécurisées
app/cognitive/    protocoles, stimuli et analyse descriptive
app/memory/       mémoire externe historique et modèles computationnels
app/research/     expériences publiées, participation et exports
app/persistence/  modèles SQLAlchemy et base SQLite
frontend/         pages HTML, CSS et modules JavaScript natifs
app/main.py       API FastAPI et service des pages
```

`MemoryModel` et les points d'extension Hopfield sont conservés, sans implémentation
neuronale. Les anciens composants de mémoire externe restent disponibles dans le backend
pour la compatibilité, mais ne font plus partie du parcours utilisateur.

## Installation locale

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --constraint requirements.lock -e '.[test,dev]'
python -m app.setup
uvicorn app.main:app --reload
```

Pour exécuter Memoriae V2, installer également les dépendances optionnelles du modèle :

```bash
python -m pip install --constraint requirements.lock -e '.[model]'
```

`python -m app.setup` demande simplement l'identifiant et le mot de passe chercheur. La
commande crée la configuration locale, sauvegarde une ancienne base si nécessaire, rattache
son schéma aux migrations et applique les mises à jour. Il n'y a aucun hash à copier.

La base par défaut est `data/memoriae.db`. Une autre URL SQLite peut être définie avec
`MEMORIAE_DATABASE_URL` avant la configuration. Les clés étrangères SQLite sont activées à
chaque connexion.

## Compte chercheur

Relancer `python -m app.setup` pour créer ou changer les identifiants. Le mot de passe est
transformé localement en hash et n'est jamais enregistré en clair. Le fichier `.env` reste
ignoré par Git.

## Interface

- `http://127.0.0.1:8000/` : accueil.
- `/participer` : rejoindre une expérience avec un code.
- `/experience` : réaliser la session en cours.
- `/connexion` : connexion chercheur.
- `/chercheur` : gérer les participants fictifs et les expériences composées de plusieurs tests.
- `/chercheur/modeles` : exécuter Memoriae V2 sur une expérience compatible.
- `/chercheur/resultats` : consulter et exporter les résultats.

Les protocoles disponibles sont le rappel verbal, la mémoire visuospatiale, la reconnaissance
de motifs, la mémoire visuelle, la mémoire associative avec indiçage sémantique et la
reconnaissance Fashion-MNIST à partir d'images masquées à 25 %, 50 % et 75 %.

## API

Les principaux endpoints sont :

```text
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
POST /api/experiments/join
GET  /api/sessions/{id}/next
POST /api/sessions/{id}/responses
POST /api/sessions/{id}/finish
GET  /api/research/experiments
POST /api/research/experiments
PATCH /api/research/experiments/{id}
DELETE /api/research/experiments/{id}
POST /api/research/experiments/{id}/duplicate
POST /api/research/experiments/{id}/launch
GET  /api/research/participants
POST /api/research/participants
PATCH /api/research/participants/{id}
DELETE /api/research/participants/{id}
GET  /api/research/results
GET  /api/research/results/{session_id}
GET  /api/research/export
GET  /api/research/models
POST /api/research/models/memoriae_v2/execute
GET  /api/research/experiments/{id}/comparison
```

La documentation interactive est disponible sur `/docs`.

Une expérience contient des tests ordonnés, chacun avec ses paramètres et son décalage de
seed. La configuration de chaque session est figée au lancement. Les participants fictifs
sont identifiés dans les résultats et les exports afin de ne pas les confondre avec les
participations autonomes.

Les données de patients, souvenirs, sessions et résultats exigent une session chercheur. Les
cookies d'accès sont `HttpOnly`, les mots de passe sont hachés avec scrypt et `.env`, les bases
SQLite et l'environnement virtuel sont exclus de Git et de l'image Docker.

## Tests

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/python demo.py
```

## Docker

Définir les variables chercheur dans l'environnement, puis :

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
docker compose run --rm backend python -m pytest
docker compose down
```

SQLite est conservée dans le volume `memoriae_data`.

## Limites

Les tâches sont des adaptations expérimentales, sans score clinique. La reproductibilité
logicielle ne garantit pas la validité scientifique. Les modèles computationnels futurs
devront être évalués séparément des observations humaines et clairement identifiés comme tels.
Memoriae V2 utilise son encodeur et son décodeur préentraînés. Pour chaque exécution, sa mémoire
associative reçoit les 12 images complètes du protocole, puis traite les 12 essais présentés dans
un ordre reproductible : quatre images différentes à chacun des niveaux de masquage 25 %, 50 %
et 75 %. Les résultats humains et computationnels restent séparés et sont reliés par
l'expérience, la version des stimuli et leurs identifiants. La MSE du modèle n'est jamais
interprétée comme un temps de réponse humain.
