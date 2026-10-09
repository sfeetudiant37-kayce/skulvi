# Talent Engine — SKULLVI HCP

Application web de collecte et de qualification de candidatures développeurs. Le projet sépare une interface accessible, une API typée, des règles métier testables et une base SQLite persistante.

## Stack

- **Frontend :** HTML sémantique, CSS responsive et JavaScript natif ; aucune dépendance CDN.
- **API :** Python 3.12+ / FastAPI / Pydantic 2.
- **Données :** SQLite, transactions, contraintes et index ; scores calculés côté serveur.
- **Exploitation :** Docker, Compose, health/readiness checks, image non-root, CI GitHub Actions, Ruff et Pytest.

L’interface s’appuie sur une palette relevée sur le site public de SKULLVI ; elle constitue une proposition de design pour le challenge, pas une charte officielle validée.

## Démarrage avec Docker Compose

```bash
cp .env.example .env
# Facultatif pour le jeu de profils fictifs : mettre SEED_SAMPLE_DATA=true dans .env
docker compose up --build
```

L’application répond sur <http://localhost:8000>. La base est conservée dans le volume Docker `talent_engine_data`. `docker compose down` arrête l’application sans supprimer ce volume.

## Parcours fonctionnel

1. Saisir le dossier dans le formulaire et valider les champs côté navigateur **et** côté API.
2. Enregistrer dans SQLite ; un e-mail normalisé unique empêche les doublons.
3. Calculer le pré-score de compétences dans le service métier (jamais fourni par le navigateur).
4. Consulter, rechercher, filtrer et paginer le pipeline.
5. Ajouter les trois notes humaines et le statut ; l’API recalcule et retourne le score final.
6. Exporter la liste au format CSV ou supprimer un dossier.

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
