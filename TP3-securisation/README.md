# TP3 — Sécurisation d'une application et supervision

Suite du TP2 (SQL Injection). Ce TP corrige les vulnérabilités identifiées et met en placeune stack de supervision complète 
(Prometheus + Loki + Grafana)

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Frontend   │────▶│  Backend Flask   │────▶│  PostgreSQL  │
│  (port 8081)│     │  (port 3001)     │     │  (port 5433)   │
└─────────────┘     └──────────────────┘     └────────────────┘
                           │                        │
                    logs /app/logs          postgres_exporter
                           │                    (port 9187)
                           ▼                        │
                      Promtail                       ▼
                           │                   Prometheus
                           ▼                   (port 9090)
                         Loki ──────────────────────┤
                      (port 3100)                    │
                                                     ▼
                                                  Grafana
                                                (port 3000)
```


## Prérequis

- Docker et Docker Compose v2
- Python 3.10+ (pour les scripts de test)
- Le TP2 doit être arrêté (`docker compose -f ../TP2-sql-injection/docker-compose.yml down`)


## 1. Démarrage

```bash
cd TP3-securisation
docker compose up -d --build
```

Attendre ~15 secondes que tous les services soient opérationnels :

```bash
docker compose ps
```

Accès :
| Service    | URL                          | Identifiants         |
|------------|------------------------------|----------------------|
| Frontend   | http://localhost:8081        | —                    |
| Backend    | http://localhost:3001/health | —                    |
| Métriques  | http://localhost:3001/metrics| —                    |
| Grafana    | http://localhost:3000        | admin / admin123     |
| Prometheus | http://localhost:9090        | —                    |


## 2. Sécurisation

### 2.1 Hachage des mots de passe (bcrypt)

Au démarrage, le backend exécute `init_db()` qui :
1. Hache chaque mot de passe avec `bcrypt.hashpw(password, bcrypt.gensalt())`
2. Insère le hash en base (format `$2b$12$...`)

Vérification en base :
```sql
docker exec -it tp3_postgres psql -U admin -d tp3_users \
  -c "SELECT username, LEFT(password, 40) || '...' AS hash FROM users;"
```

### 2.2 Requêtes préparées (psycopg2)

**TP2 — vulnérable** :
```python
query = f"SELECT ... WHERE username = '{username}' AND password = '{password}'"
cur.execute(query)
```

**TP3 — sécurisé** :
```python
cur.execute(
    "SELECT ... FROM users WHERE username = %s",
    (username,)   # paramètre transmis séparément, jamais concaténé
)
```

---

## 3. Tests

### Installation des dépendances Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests
```

### 3.1 Tests de connexion

```bash
python test_secure.py
```

Teste : connexions valides, mauvais mots de passe, métriques Prometheus.

### 3.2 Rejeu des injections du TP2

```bash
python test_injection_replay.py
```

Rejoue les 6 vecteurs d'attaque du TP2. Tous doivent être **neutralisés** (401).

### 3.3 Comparaison TP2 / TP3

| Vecteur d'attaque            | TP2 (vulnérable) | TP3 (sécurisé) |
|------------------------------|-----------------|----------------|
| `' OR '1'='1`                | Connexion accordée — 5 comptes exposés | 401 Refusée |
| `admin'--`                   | Connexion admin sans mot de passe | 401 Refusée |
| `' OR 1=1--`                 | Toutes les lignes retournées | 401 Refusée |
| Guillemet seul `'`           | Erreur SQL exposée (500) | 401 Refusée |

---

## 4. Journalisation

### Logs applicatifs (JSON structuré)

```bash
docker logs tp3_backend
# ou
cat logs/app.log
```

Format d'un enregistrement :
```json
{"timestamp": "2025-01-01T12:00:00Z", "event": "LOGIN_FAILURE",
 "username": "' OR '1'='1", "success": false, "ip": "172.18.0.1",
 "details": "invalid credentials"}
```

Événements journalisés :
- `SERVER_START` — démarrage du serveur
- `DB_INIT` — initialisation de la base
- `LOGIN_SUCCESS` — connexion réussie
- `LOGIN_FAILURE` — mauvais identifiants
- `LOGIN_ERROR` — erreur interne

### Logs PostgreSQL

```bash
docker logs tp3_postgres
```

Les connexions, déconnexions et erreurs sont journalisées grâce aux paramètres
`log_connections=on`, `log_disconnections=on`, `log_failed_connections=on`.

### Logs Docker (tous les conteneurs)

```bash
docker compose logs -f
```


## 5. Supervision avec Grafana

### 5.1 Accès au dashboard

1. Ouvrir http://localhost:3000
2. Se connecter : `admin` / `admin123`
3. Aller dans **Dashboards → TP3 → TP3 — Supervision Sécurité**

### 5.2 Panels disponibles

| Panel                             | Source     | Métrique                                   |
|-----------------------------------|------------|--------------------------------------------|
| Connexions réussies (1h)          | Prometheus | `login_attempts_total{status="success"}`   |
| Connexions échouées (1h)          | Prometheus | `login_attempts_total{status="failure"}`   |
| Connexions PG actives             | Prometheus | `pg_stat_activity_count`                   |
| Taux d'erreurs (1h)               | Prometheus | `login_attempts_total{status="error"}`     |
| Tentatives de connexion (graphe)  | Prometheus | `rate(login_attempts_total[1m])`           |
| Transactions PostgreSQL / s       | Prometheus | `rate(pg_stat_database_xact_commit_total)` |
| Logs en temps réel                | Loki       | `{job="tp3-app"}`                          |
| Tentatives échouées (logs)        | Loki       | `{job="tp3-app"} \|= "LOGIN_FAILURE"`      |

### 5.3 Simuler une attaque et observer dans Grafana

```bash
# Lancer des tentatives d'injection
python test_injection_replay.py

# Observer dans Grafana :
# - Les compteurs "Connexions échouées" augmentent
# - Les logs montrent les payloads d'injection
# - Les métriques Prometheus enregistrent les tentatives
```


## 6. Questions d'analyse

**Q1 — Apport du hachage des mots de passe ?**
Même en cas de fuite de la base de données, les mots de passe restent inutilisables.
bcrypt est lent par conception (coût configurable) ce qui ralentit les attaques
par force brute. Le sel intégré rend les tables arc-en-ciel inefficaces.

**Q2 — Pourquoi les requêtes préparées empêchent-elles les injections SQL ?**
Le plan de la requête est compilé avant la réception des paramètres.
La valeur passée via `%s` ne peut jamais modifier la structure SQL :
elle est traitée comme une donnée, pas comme du code.

**Q3 — Le hachage seul protège-t-il contre les injections SQL ?**
Non. Le hachage protège les mots de passe *stockés* mais ne change pas
la logique de construction de la requête SQL. Un payload `' OR '1'='1`
contourne la condition sans même connaître de mot de passe.

**Q4 — Quels événements doivent être journalisés ?**
- Tentatives de connexion (succès et échecs) avec horodatage et IP
- Erreurs d'application (exceptions, erreurs BDD)
- Démarrages et arrêts du service
- Modifications de données sensibles (création/suppression de comptes)
- Dépassements de seuils (nombre d'échecs consécutifs = brute force)

**Q5 — Quelles métriques Grafana permettent de détecter une activité suspecte ?**
- Pic de `login_attempts_total{status="failure"}` → brute force
- Ratio échecs/succès > 10:1 → attaque automatisée
- IP unique avec grand nombre de tentatives → ciblage
- Augmentation soudaine de `pg_stat_activity_count` → connexions anormales
- Logs contenant des guillemets ou mots-clés SQL → tentatives d'injection

**Q6 — Recommandations supplémentaires**
- Limiter le taux de tentatives par IP (rate limiting)
- Implémenter un verrouillage de compte après N échecs
- Utiliser HTTPS (TLS) pour chiffrer les échanges
- Restreindre les permissions DB (utilisateur dédié, accès minimal)
- Ajouter un CAPTCHA sur le formulaire de connexion
- Activer l'authentification à deux facteurs pour les comptes admin
- Scanner régulièrement avec OWASP ZAP ou Trivy


