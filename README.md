# HealthPredict AI — Sécurisation d'une application web

Projet fil rouge réalisé dans le cadre d'un cursus de cybersécurité. L'objectif est de partir d'une application web manipulant des données personnelles et de santé, de l'attaquer, de la sécuriser, puis de la gouverner — du code jusqu'au RGPD.

L'application simulée, **HealthPredict AI**, est un système d'authentification connecté à une base PostgreSQL contenant des données personnelles, de santé et bancaires. C'est volontairement un cas concret : le genre de données qui, en cas de fuite, expose une entreprise à des sanctions réglementaires et des conséquences réputationnelles sérieuses.


## Ce que contient ce dépôt

```
cartographie/
├── Analyse_du_Système_de_Données.md   # TP1 — Cartographie des flux et classification RGPD
├── conformite_reglementation/         # TP1 — Rapport de conformité RGPD / risques cloud
├── TP2-sql-injection/                 # TP2 — Application volontairement vulnérable
├── TP3-securisation/                  # TP3 — Application sécurisée + stack de supervision
├── TP4-gouvernance/                   # TP4 — Audit, gouvernance et plan d'amélioration
└── healthpredict_flux.drawio.png      # Schéma des flux de données
```

Chaque dossier TP est autonome avec son propre `docker-compose.yml` et son `README.md`.


## Les 4 travaux pratiques

### TP1 — Cartographie des données

Analyse complète du système HealthPredict AI : identification des flux de données entre l'utilisateur, le frontend, l'API backend, le modèle IA et le stockage AWS S3. Classification des données selon leur sensibilité RGPD, identification des acteurs du traitement (responsable, sous-traitant), et évaluation des risques cloud.

Point central : les données de santé relèvent de l'article 9 du RGPD — leur traitement est soumis à des conditions strictes et nécessite une AIPD (Analyse d'Impact).


### TP2 — Injection SQL

Démonstration concrète d'une injection SQL sur une application volontairement vulnérable. La faille vient de la construction de requêtes par concaténation directe :

```python
# Code vulnérable — le payload est interprété comme du SQL
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

Avec le payload `' OR '1'='1`, la condition devient toujours vraie. Résultat : tous les comptes sont exposés, mots de passe en clair inclus, sans connaître le moindre identifiant.

**Lancer l'environnement vulnérable :**

```bash
cd TP2-sql-injection 
docker compose up -d
```

| Service | URL |
|---|---|
| Frontend (interface de login) | http://localhost:8080 |
| Backend API | http://localhost:3002 |

**Lancer les tests d'injection :**

```bash
source venv/bin/activate
python test_injection.py
```


### TP3 — Sécurisation et supervision

Correction des vulnérabilités du TP2 et déploiement d'une stack de supervision complète.

**Deux corrections fondamentales :**

1. **Requêtes préparées** — le paramètre n'est plus jamais concaténé dans la chaîne SQL :
```python
cur.execute("SELECT * FROM users WHERE username = %s", (username,))
```

2. **Hachage bcrypt** — les mots de passe sont hachés avec un sel avant stockage :
```
alice2024  →  $2b$12$xK7pL3mN9qR2vW8tY1uZ4e...
```

**Stack de supervision :**

```
Flask ──► /metrics ──► Prometheus ──► Grafana  (métriques temps réel)
Flask ──► app.log  ──► Promtail   ──► Loki ──► Grafana  (logs structurés)
PostgreSQL ──► postgres_exporter ──► Prometheus
```

**Lancer l'environnement sécurisé :**

```bash
cd TP3-securisation
docker compose up -d --build
```

| Service | URL | Identifiants |
|---|---|---|
| Frontend | http://localhost:8081 | — |
| Backend API | http://localhost:3001 | — |
| Grafana | http://localhost:3000 | admin / admin123 |
| Prometheus | http://localhost:9090 | — |

**Vérifier que les injections sont bloquées :**

```bash
source venv/bin/activate
python test_injection_replay.py   # rejoue les 6 vecteurs du TP2 → tous 401
python test_secure.py             # vérifie les connexions légitimes
```

| Vecteur d'attaque | TP2 | TP3 |
|---|---|---|
| `' OR '1'='1` | Connexion accordée, 5 comptes exposés | 401 Refusée |
| `admin'--` | Compte admin sans mot de passe | 401 Refusée |
| `' OR 1=1--` | Toutes les lignes retournées | 401 Refusée |
| `' UNION SELECT ...` | Exfiltration de données possible | 401 Refusée |
| Guillemet seul `'` | Erreur SQL 500 exposée | 401 Refusée |


### TP4 — Gouvernance, audit et amélioration continue

Audit complet de l'application et définition d'un cadre de gouvernance.

**Documents produits :**

| Fichier | Contenu |
|---|---|
| `rapport_audit.md` | Audit des logs PostgreSQL, Docker et applicatifs |
| `politique_gouvernance.md` | Rôles, règles de gestion et droits sur les données |
| `strategie_sauvegarde.md` | Plan de sauvegarde 3-2-1, RPO/RTO |
| `plan_amelioration.md` | Feuille de route priorisée en 4 phases |

**Résultat de l'audit:** 11 connexions réussies, 11 échecs dont 6 injections SQL toutes bloquées et tracées. Points ouverts : absence de rate limiting, un seul utilisateur DB (moindre privilège non respecté).


## Architecture technique

```
┌─────────────────────────────────────────────────────────────┐
│  TP2 — Environnement VULNÉRABLE          (ports 8080, 3002)  │
│                                                              │
│  Nginx (frontend) ──► Flask (backend) ──► PostgreSQL        │
│                       requêtes concaténées                   │
│                       mots de passe en clair                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  TP3 — Environnement SÉCURISÉ   (ports 8081, 3001, 3000)    │
│                                                              │
│  Nginx ──► Flask ──► PostgreSQL                             │
│            │         requêtes préparées                      │
│            │         mots de passe bcrypt                    │
│            │                                                 │
│            ├──► Prometheus ──► Grafana (métriques)          │
│            └──► Promtail ──► Loki ──► Grafana (logs)        │
└─────────────────────────────────────────────────────────────┘
```


## Stack technologique

| Composant | Technologie | Version |
|---|---|---|
| Backend | Python / Flask | 3.12 |
| Base de données | PostgreSQL | 16 |
| Frontend | HTML / JS servi par Nginx | 1.25 |
| Conteneurisation | Docker / Docker Compose | — |
| Métriques | Prometheus | 2.50 |
| Logs | Loki + Promtail | 2.9 |
| Dashboards | Grafana | 10.4 |
| Hachage | bcrypt | — |
| Driver DB | psycopg2 | — |


## Prérequis

- Docker et Docker Compose installés
- Python 3.10+ avec `pip` (pour les scripts de test)
- Les ports 3000, 3001, 3002, 8080, 8081, 9090 disponibles


## Démarrage rapide (les deux environnements en parallèle)

```bash
# 1. Cloner le dépôt
git clone <url-du-depot>
cd cartographie

# 2. Créer le virtualenv Python pour les tests
python3 -m venv venv
source venv/bin/activate
pip install requests

# 3. Lancer l'environnement vulnérable (TP2)
cd TP2-sql-injection && docker compose up -d && cd ..

# 4. Lancer l'environnement sécurisé + supervision (TP3)
cd TP3-securisation && docker compose up -d --build && cd ..

# 5. Vérifier que tout répond
curl -s http://localhost:3002/health   # TP2
curl -s http://localhost:3001/health   # TP3
```

Attendre ~20 secondes après le lancement de TP3 pour que PostgreSQL soit prêt et que Grafana charge ses dashboards.


## Accès RGPD et conformité

Les données traitées par HealthPredict AI incluent des données de santé au sens de l'article 9 du RGPD. Le projet TP1 documente :

- la cartographie complète des flux de données
- la classification par niveau de sensibilité
- les obligations légales applicables (AIPD, registre des traitements, notification CNIL sous 72h)
- les risques liés à l'hébergement cloud (AWS S3) et les mécanismes de conformité disponibles (DPF, CCT)


## Arrêter les environnements

```bash
cd TP2-sql-injection && docker compose down && cd ..
cd TP3-securisation  && docker compose down && cd ..
```

Pour supprimer également les volumes (reset complet des bases) :

```bash
docker compose down -v
```
