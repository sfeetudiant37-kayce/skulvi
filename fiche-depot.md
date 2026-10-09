# Fiche de dépôt — mini-challenge SKULLVI

## Ce que demande l’épreuve

Votre candidature passe à l’évaluation pratique. Le mini-projet consiste à structurer les candidatures, calculer un score explicable, les classer et donner une priorité d’examen. L’équipe insiste sur un projet simple, compris et documenté. Il n’y a pas de promesse de sélection : les réalisations seront examinées.

## Projet livré

**Talent Engine** est un MVP full-stack : interface web responsive, API FastAPI typée, validation Pydantic, règles de scoring isolées et base SQLite persistante. Le projet comprend également des tests automatisés, Docker/Compose, un endpoint readiness, une CI et une note de conception.

### Fichiers à consulter

- `web/` : interface et assets.
- `app/` : API, modèles de données, service métier, scoring, repository et base.
- `tests/` : tests Pytest.
- `README.md` : installation, lancement, API et limites.
- `CONCEPTION.md` : compréhension du besoin, schéma de données, scoring, erreurs, tests et exploitation.
- `Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml` : éléments DevOps.

Avant dépôt :

- [ ] Lancer le projet et essayer ajout, recherche, filtre, pagination, revue, export, édition et suppression.
- [ ] Exécuter `pytest` et `ruff check app tests` ; vérifier que tout passe.
- [ ] Lire `/api/docs` et expliquer les routes, la validation serveur, la base et les codes d’erreur.
- [ ] Comprendre le calcul `/40 + /60`, ses hypothèses et le fait que les déclarations de compétences doivent être vérifiées.
- [ ] Personnaliser et tester au moins un choix à votre façon ; notez précisément ce que vous avez personnellement changé.
- [ ] Ne déployez pas cette version sans authentification avec de vraies candidatures. Les profils préchargés sont fictifs.
- [ ] Déposez les fichiers source, instructions de lancement et éventuels liens de dépôt sur Monday.

### Démarrage rapide

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
SEED_SAMPLE_DATA=true uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

Ouvrir `http://localhost:8000` ; documentation API sur `http://localhost:8000/api/docs`.

## Votre projet personnel — à compléter avec un vrai projet

Le mini-challenge ne remplace pas la présentation d’un projet que vous avez personnellement réalisé. Remplissez ces champs avec des faits réels :

- **Nom et présentation :** [à compléter]
- **Problème/besoin traité :** [à compléter]
- **Mon rôle exact :** [à compléter]
- **Ce que j’ai personnellement réalisé :** [à compléter]
- **Technologies et outils :** [à compléter]
- **Défi, solution et résultat :** [à compléter]
- **GitHub/GitLab/portfolio/démo :** [à compléter]
- **Vidéo :** facultative selon l’e-mail.

## Déclaration d’utilisation de l’IA

Le code initial de ce projet a été créé et remanié avec l’aide d’un assistant IA. Avant le dépôt, remplacez le texte entre crochets par ce que vous avez réellement vérifié, modifié et appris. Ne revendiquez pas une contribution que vous n’avez pas faite.

> J’ai utilisé un assistant IA pour m’aider à produire une première version de l’interface, de l’API et de la documentation. J’ai personnellement **[indiquer les changements réellement effectués]**, exécuté **[tests réellement lancés]** et vérifié **[points réellement compris]**. Je peux expliquer les règles métier, la persistance SQLite, les validations et les limites de cette version.

## Proposition de présentation orale (45–60 s)

1. Expliquer le besoin : rendre les candidatures structurées et comparables.
2. Montrer le pipeline et créer un dossier.
3. Décrire la séparation : interface → API validée → service de score → SQLite.
4. Expliquer le pré-score déclaratif `/40`, la revue humaine `/60`, puis les seuils indicatifs sans rejet automatique.
5. Montrer les tests, Docker/healthcheck et les limites restantes : pas d’authentification ni de politiques de conservation, donc pas de vraies données dans cet environnement.
