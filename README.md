# Talent Engine — SKULLVI HCP

Application web de collecte et de qualification de candidatures développeurs. Le projet sépare une interface accessible, une API typée, des règles métier testables et une base SQLite persistante.

## Stack

- **Frontend :** HTML sémantique, CSS responsive et JavaScript natif ; aucune dépendance CDN.
- **API :** Python 3.12+ / FastAPI / Pydantic 2.
- **Données :** SQLite, transactions, contraintes et index ; scores calculés côté serveur.
- **Exploitation :** Docker, Compose, health/readiness checks, image non-root, CI GitHub Actions, Ruff et Pytest.

L’interface s’appuie sur une palette relevée sur le site public de SKULLVI ; elle constitue une proposition de design pour le challenge, pas une charte officielle validée.

## Démarrage local

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\\Scripts\\activate
python -m pip install -r requirements-dev.txt
SEED_SAMPLE_DATA=true uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

Ouvrir <http://localhost:8000>. La première exécution crée `data/talent_engine.sqlite3`. La variable `SEED_SAMPLE_DATA=true` précharge quatre profils fictifs, une seule fois, si la base est vide. Sans cette variable, l’application démarre avec une base vide.

- Documentation interactive de l’API : <http://localhost:8000/api/docs>
- Santé du processus : <http://localhost:8000/healthz>
- Readiness (inclut le contrôle SQLite) : <http://localhost:8000/readyz>
- Santé versionnée : <http://localhost:8000/api/v1/health>

## Démarrage avec Docker Compose

```bash
cp .env.example .env
# Facultatif pour le jeu de profils fictifs : mettre SEED_SAMPLE_DATA=true dans .env
docker compose up --build
```

L’application répond sur <http://localhost:8000>. La base est conservée dans le volume Docker `talent_engine_data`. `docker compose down` arrête l’application sans supprimer ce volume.

## Push GitHub

Le dépôt cible configuré pour ce livrable est `sfeetudiant37-kayce/skulvi`. Depuis le dossier extrait, avec Git et [GitHub CLI](https://cli.github.com/) installés, lance :

```bash
bash ./push-to-github.sh
```

Le script utilise l’authentification sécurisée de GitHub CLI (flux navigateur), demande le nom et l’e-mail de l’auteur si nécessaire, puis pousse `main`. Il ne demande ni n’enregistre de token dans le code.

## Vérifications de qualité

```bash
pytest
ruff check app tests
```

La suite comprend **16 tests** : calcul des scores, validation, unicité des e-mails, opérations CRUD, revue et statut, recherche/filtres/pagination, export CSV, en-têtes de sécurité, indicateurs du pipeline, santé de l’API et idempotence du seed. La CI exécute ces commandes sur Python 3.12 et 3.13.

## Parcours fonctionnel

1. Saisir le dossier dans le formulaire et valider les champs côté navigateur **et** côté API.
2. Enregistrer dans SQLite ; un e-mail normalisé unique empêche les doublons.
3. Calculer le pré-score de compétences dans le service métier (jamais fourni par le navigateur).
4. Consulter, rechercher, filtrer et paginer le pipeline.
5. Ajouter les trois notes humaines et le statut ; l’API recalcule et retourne le score final.
6. Exporter la liste au format CSV ou supprimer un dossier.

## Barème de qualification

Le message de recrutement ne fournit pas de critères officiels. Le barème est donc une **proposition à faire valider** avant usage réel.

- **Compétences déclarées : 40 points.** Quatre compétences de référence par parcours, 10 points par correspondance. C’est un pré-score déclaratif, pas une preuve de maîtrise.
- **Revue humaine : 60 points.** Projet/contribution `/25`, motivation/compréhension `/20`, apprentissage/autonomie `/15`. Repères et détails dans la fiche du candidat et la fenêtre **Critères d’évaluation**.
- **Final :** disponible lorsque les trois notes humaines sont définies, même si une note vaut zéro.
- **Priorité indicative :** 75–100 priorité suggérée ; 55–74 à examiner ; 0–54 à compléter. Avant revue complète, l’indice est le pré-score de compétences normalisé. Aucun candidat n’est rejeté automatiquement.

Les années d’expérience, le nombre de projets, l’existence d’un lien et la disponibilité restent des informations de contexte, sans points.

## API v1

| Méthode | Route | Usage |
|---|---|---|
| `GET` | `/api/v1/meta` | Environnement et présence de profils fictifs |
| `GET` | `/api/v1/options` | Parcours, compétences, statuts et disponibilités |
| `GET` | `/api/v1/stats` | Indicateurs du pipeline |
| `GET` | `/api/v1/candidates` | Recherche, filtres et pagination |
| `POST` | `/api/v1/candidates` | Créer une candidature |
| `GET` | `/api/v1/candidates/{id}` | Lire un dossier |
| `PUT` | `/api/v1/candidates/{id}` | Modifier les informations de candidature |
| `PATCH` | `/api/v1/candidates/{id}/review` | Enregistrer notes et statut |
| `DELETE` | `/api/v1/candidates/{id}` | Supprimer un dossier |
| `GET` | `/api/v1/candidates/export.csv` | Export CSV |
| `GET` | `/api/v1/health` | Vérifier API et base |

## Architecture et choix

```text
web/                 Interface statique, même origine
app/api.py           Contrat HTTP, routes et codes d’erreur
app/schemas.py       Validation d’entrée/sortie avec Pydantic
app/services.py      Cas d’usage et orchestration
app/scoring.py       Logique métier pure, déterministe et testée
app/repositories.py  Requêtes SQL paramétrées
app/db.py            Connexions, transactions et schéma versionné
```

FastAPI sert l’interface et l’API sur la même origine : pas de CORS large ni de clés secrètes dans le navigateur. SQLite est un choix adapté à un premier déploiement mono-instance ; le moteur de scoring est isolé pour permettre une évolution vers PostgreSQL ou un autre stockage sans réécrire les règles métier.

## Limites et sécurité

Cette livraison est un **MVP fonctionnel pour le challenge**, pas un service RH prêt à recevoir des candidatures réelles. L’instance fournie n’a ni authentification, ni gestion de rôles, ni chiffrement applicatif, ni politique de conservation intégrée ; elle ne doit pas être exposée publiquement avec des données personnelles. Le serveur ajoute des en-têtes de sécurité, valide les données et utilise des requêtes SQL paramétrées, mais ces mesures ne remplacent pas une vraie politique d’accès.

Avant production : ajouter une authentification/autorisation, HTTPS et secrets gérés, sauvegardes/restauration, journal d’audit, durée de conservation/suppression, surveillance, protection des exports, revue des biais du barème et validation juridique/confidentialité.
