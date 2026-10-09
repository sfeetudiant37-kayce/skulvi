# Note de conception — Talent Engine

## 1. Compréhension du problème

Les candidatures peuvent arriver sous des formats différents ; l’équipe a besoin de les centraliser, de structurer les informations utiles et de décider dans quel ordre examiner les profils. La solution doit réduire le travail de tri manuel sans transformer une note en décision automatique.

### Périmètre du premier incrément

- créer, lire, modifier, rechercher, filtrer, paginer, évaluer et supprimer un dossier ;
- conserver les candidatures sur un serveur local dans SQLite ;
- rapprocher des compétences déclarées avec le parcours choisi ;
- compléter ce pré-score avec une revue humaine explicable ;
- exposer les indicateurs et l’export CSV ;
- documenter les limites de confidentialité et d’exploitation.

Pas de moteur d’IA, de rejet automatique, de gestion de plusieurs organisations ou de workflow d’approbation complexe : ces fonctions ne sont pas nécessaires au mini-challenge.

## 2. Parcours d’usage

```text
Saisie du profil
  → validation navigateur
  → validation API (Pydantic)
  → unicité de l’e-mail + transaction SQLite
  → pré-score par service métier
  → recherche / filtre / pagination
  → revue humaine et statut
  → score final recalculé côté serveur
  → export CSV ou suppression
```

Statuts opérationnels : `Nouveau`, `En analyse`, `Présélectionné`, `À compléter`, `Clôturé`. Ils sont distincts du score et sont changés par une personne. Ils ne déclenchent pas de refus automatique.

## 3. Architecture

```text
Navigateur
  ├── web/index.html + assets/styles.css + assets/app.js
  └── appels même origine /api/v1/*
              ↓
FastAPI (contrat HTTP)
  ├── Pydantic : entrées/sorties et contraintes
  ├── service : cas d’usage + score calculé serveur
  ├── scoring : fonctions pures et déterministes
  └── repository : SQL paramétré, transactions SQLite
              ↓
SQLite (schéma versionné, volume Docker)
```

Le frontend est livré séparément du code API, mais servi par la même application pour éviter un CORS permissif et permettre un aperçu avec une seule origine. Le score n’est jamais accepté comme valeur fournie par le navigateur : l’API le recalcule pour les réponses et le classement.

## 4. Modèle de données

Une ligne `candidates` contient :

| Groupe | Champs |
|---|---|
| Identité | `id`, `name`, `email`, `email_normalized`, `created_at`, `updated_at` |
| Parcours | `track`, `skills_json`, `other_skills`, `experience_years`, `availability` |
| Preuves | `project_count`, `portfolio_url`, `project_summary`, `motivation` |
| Workflow | `status`, `review_notes`, `is_sample` |
| Revue humaine | `review_project` (0–25), `review_motivation` (0–20), `review_learning` (0–15) |

Contraintes : clé primaire UUID, adresse e-mail normalisée unique, valeurs numériques bornées, champs requis validés, options de parcours/statut énumérées. Les colonnes de score final et de tri ne sont pas stockées : elles sont dérivées à la lecture à partir des critères versionnés, ce qui évite les valeurs périmées lorsqu’un calcul change.

Les années d’expérience, la disponibilité, le nombre de projets et le lien sont consultables comme contexte, sans ajouter de points. Aucune donnée sensible (âge, genre, origine, photo) n’est demandée.

## 5. Logique de qualification et de scoring

Le message SKULLVI ne donne pas de barème officiel. Les pondérations suivantes sont une proposition pour le mini-projet et doivent être validées par l’équipe avant usage réel.

### Pré-score déclaratif — 40 points

Chaque parcours définit quatre compétences de référence. Une correspondance vaut 10 points. La normalisation ignore la casse et les accents.

```text
skill_score = nombre de compétences de référence déclarées × 10
```

Le signal est utile pour une première organisation, mais il n’est pas une vérification technique. Les compétences doivent être confirmées à partir des travaux du candidat ou d’un échange.

### Revue humaine — 60 points

| Dimension | Maximum | Repères |
|---|---:|---|
| Projet et contribution personnelle | 25 | Rôle exact, pertinence, raisonnement, résultat et limites |
| Motivation et compréhension | 20 | Objectif d’apprentissage concret, motivation spécifique et réaliste |
| Apprentissage et autonomie | 15 | Initiative, méthode face à un obstacle, feedback et progression |

Le score final n’est calculé que lorsque les trois champs ont une valeur, y compris zéro. `final_score = skill_score + review_project + review_motivation + review_learning`.

Le nombre de projets, la présence d’un lien, l’expérience en années et la disponibilité ne modifient pas le score : les compter directement risquerait de confondre accès aux ressources ou ancienneté avec potentiel.

### Indice de tri

- 75–100 : priorité suggérée ;
- 55–74 : à examiner ;
- 0–54 : à compléter.

Avant revue complète, `triage_index = round(skill_score / 40 × 100)` et l’interface l’étiquette `pré-score`. Après revue, il devient le score final. Le statut reste indépendant. Les seuils servent à répartir l’attention, jamais à éliminer automatiquement une personne.

## 6. Contrat API et erreurs

`/api/v1/candidates` offre la création et une liste avec `q`, `track`, `status`, `page`, `page_size`. `PUT /{id}` modifie le profil ; `PATCH /{id}/review` modifie les notes humaines et le statut. `/stats`, `/options`, `/health` et `/candidates/export.csv` répondent aux besoins de l’interface.

| Cas | Réponse attendue |
|---|---|
| Données invalides (e-mail, motivation, URL, bornes, option inconnue) | `422` et détails de validation |
| Adresse e-mail déjà enregistrée, sans distinguer la casse | `409 Conflict` |
| Identifiant inconnu | `404 Not Found` |
| Base inaccessible | `503 Service Unavailable` sur le contrôle de santé |
| Revue humaine incomplète | Dossier enregistré, mais `final_score = null` |
| Erreur inattendue | Erreur serveur générique, sans afficher de trace interne à l’utilisateur |

Les requêtes SQL sont paramétrées ; le contenu utilisateur est échappé avant rendu HTML et les URL sont limitées à HTTP(S).

## 7. Tests et qualité

Les tests Pytest couvrent scoring, validation, unicité, CRUD, recherche, filtres, pagination, revue, export, santé et seed idempotent. Ruff est exécuté par la CI sur Python 3.12 et 3.13.

Vérifications manuelles recommandées : ajout avec champs invalides, doublon e-mail, lien dangereux, changement de parcours, revue partielle et complète, statut, filtre/pagination, export CSV, redémarrage API avec persistance SQLite, contrôle `/readyz` et démarrage Docker.

## 8. Exploitation et direction visuelle

- Configuration par variables d’environnement ; pas de secret dans le dépôt.
- SQLite avec schéma versionné, timeout d’attente et volume Docker persistant.
- Processus Uvicorn écoutant sur `0.0.0.0`, healthcheck, container non-root, `no-new-privileges`, suppression des capabilities inutiles.
- En-têtes CSP, `X-Content-Type-Options`, `Referrer-Policy` et `Permissions-Policy` ; API et UI sur la même origine.
- CI GitHub Actions : installation, lint et tests.
- Palette adaptée à partir des couleurs visibles sur <https://www.skullvi.org/> : encre `#01010C`, vert `#008838`, orange `#F39200`, bleu `#236CB4`, corail `#E14313`, fonds `#F8F9FA`/`#F2F7F2`. Le traitement typographique privilégie Inter / IBM Plex Sans avec une pile système de secours. C’est une interprétation du site public, pas un fichier de charte validé.

## 9. Limites à ne pas masquer

L’application est un MVP fonctionnel du challenge, pas un service RH prêt pour les données réelles : aucune authentification ou gestion de rôles n’est implémentée, les sauvegardes et la durée de conservation ne sont pas configurées, et SQLite est prévu ici pour une instance simple. Docker et les contrôles de santé rendent le lancement reproductible, mais ne remplacent pas ces contrôles de production.

Avant toute utilisation réelle : authentification/autorisation, HTTPS, gestion de secrets, sauvegardes/restauration, journal d’audit, suppression planifiée, monitoring, politique de confidentialité, revue de biais et, en cas de déploiement concurrent à plus grande échelle, base PostgreSQL et migrations formelles.
