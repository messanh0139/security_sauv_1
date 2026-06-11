# Rapport d'audit — Base de données et application

**Périmètre :** Application HealthPredict AI — TP3 (version sécurisée)  
**Date d'audit :** Juin 2026  
**Sources analysées :** logs applicatifs (`app.log`), logs PostgreSQL (`docker logs tp3_postgres`), logs Docker

---

## 1. Méthodologie

L'audit a porté sur trois sources de données :

1. **Logs applicatifs** (`/app/logs/app.log`) — événements d'authentification au format JSON
2. **Logs PostgreSQL** — connexions, déconnexions, erreurs de la base de données
3. **Logs Docker** — état des conteneurs et événements d'infrastructure

L'objectif était de vérifier que les mesures de sécurité déployées en TP3 fonctionnent
comme prévu, de détecter d'éventuelles anomalies et d'évaluer la complétude de la
journalisation.

---

## 2. Analyse des logs applicatifs

### 2.1 Statistiques générales

Sur la période observée (10 juin 2026, 09h00 — 09h44 UTC) :

| Événement | Nombre | Observations |
|---|:---:|---|
| `LOGIN_SUCCESS` | 11 | Connexions légitimes — alice, bob, charlie, admin, diana |
| `LOGIN_FAILURE` | 11 | Dont 6 tentatives d'injection SQL identifiées |
| `SERVER_START` | 1 | Démarrage normal à 08h54 UTC |
| `DB_INIT` | 1 | Initialisation avec hachages bcrypt confirmée |
| `LOGIN_ERROR` | 0 | Aucune erreur serveur — stabilité satisfaisante |

### 2.2 Tentatives d'attaque détectées

Six tentatives d'injection SQL ont été enregistrées depuis l'adresse IP `172.21.0.1`
à 09h44 UTC, en l'espace de moins d'une seconde (attaque automatisée) :

| Horodatage | Payload injecté | Résultat |
|---|---|:---:|
| 09:44:14.216 | `' OR '1'='1` | 401 — Bloqué |
| 09:44:14.239 | `admin'--` | 401 — Bloqué |
| 09:44:14.261 | `' OR 1=1--` | 401 — Bloqué |
| 09:44:14.283 | `' UNION SELECT 1,'hacker','hash',4,'admin'--` | 401 — Bloqué |
| 09:44:14.911 | `alice` (mauvais mot de passe) | 401 — Bloqué |
| 09:44:14.932 | `'` (guillemet seul) | 401 — Bloqué |

**Constat :** toutes les tentatives ont été correctement bloquées et journalisées.
Les requêtes préparées ont rempli leur rôle. Le payload le plus sophistiqué
(`UNION SELECT`) a lui aussi été neutralisé sans provoquer d'erreur serveur.

### 2.3 Comportements anormaux identifiés

- **Concentration temporelle** : les 6 attaques en 716 millisecondes indiquent un outil
  automatisé (script Python ou scanner). Dans un environnement de production, ce comportement
  déclencherait un rate limiting et un bannissement de l'IP.

- **IP unique** : toutes les tentatives proviennent de `172.21.0.1` (passerelle Docker).
  En production, cette IP serait celle de l'attaquant et permettrait un blocage ciblé.

- **Absence de verrouillage** : après 11 échecs consécutifs, le compte alice n'a pas été
  verrouillé. L'application ne dispose pas encore de cette protection.

---

## 3. Analyse des logs PostgreSQL

### 3.1 Activité générale

Les logs PostgreSQL montrent un fonctionnement normal avec :
- Des connexions régulières de `pg_isready` (health check Docker toutes les 5 secondes)
- Des connexions applicatives courtes depuis `172.21.0.7` (backend Flask)
- Une session longue de 5h42 min (connexion persistante du backend)
- Un arrêt propre (`fast shutdown`) à 14h37 UTC

### 3.2 Mécanismes d'authentification

L'authentification PostgreSQL utilise **SCRAM-SHA-256**, confirmé dans les logs :
```
connection authenticated: identity="admin" method=scram-sha-256
```
C'est le mécanisme le plus sécurisé disponible dans PostgreSQL 16. Les mots de passe
ne transitent jamais en clair entre l'application et la base.

### 3.3 Points d'attention

- **Un seul utilisateur DB** : l'utilisateur `admin` est utilisé pour toutes les opérations
  (health checks, requêtes applicatives, exports). Le principe du moindre privilège n'est
  pas appliqué.

- **Connexions non chiffrées (TLS)** : les logs ne mentionnent pas de chiffrement TLS
  entre le backend et PostgreSQL. En production sur un réseau partagé, ce serait un risque.

- **Pas de log des requêtes SQL** : les requêtes exécutées ne sont pas journalisées
  (`log_statement` n'est pas activé). En cas d'incident, il serait impossible de reconstituer
  précisément ce qui a été lu ou modifié.

---

## 4. Analyse des logs Docker

### 4.1 État des conteneurs

Tous les conteneurs de la stack TP3 ont fonctionné sans interruption durant la période auditée :

| Conteneur | Uptime observé | Statut |
|---|---|:---:|
| `tp3_backend` | 46 min | Stable |
| `tp3_postgres` | 47 min | Stable (healthy) |
| `tp3_grafana` | 47 min | Stable |
| `tp3_prometheus` | 47 min | Stable |
| `tp3_loki` | 47 min | Stable |
| `tp3_promtail` | 47 min | Stable |
| `tp3_postgres_exporter` | 46 min | Stable |
| `tp3_frontend` | 46 min | Stable |

### 4.2 Points d'attention

- **Absence de restart policy** : si un conteneur plante, il ne redémarre pas automatiquement.
  En production, `restart: unless-stopped` ou `restart: always` devrait être configuré.

- **Volumes non sauvegardés** : les données PostgreSQL sont dans un volume Docker non sauvegardé.
  Un `docker compose down -v` effacerait l'ensemble des données sans possibilité de restauration.

- **Ports exposés publiquement** : Grafana (3000), Prometheus (9090) et Loki (3100) sont
  accessibles depuis l'extérieur sans authentification (sauf Grafana). En production, ces
  ports devraient être filtrés par un pare-feu.

---

## 5. Synthèse de l'audit

### Ce qui fonctionne bien

| Mesure | Statut | Preuve |
|---|:---:|---|
| Requêtes préparées | ✅ Efficace | 6 injections bloquées, aucun accès non autorisé |
| Hachage bcrypt | ✅ En place | `DB_INIT: seeded with bcrypt hashes` confirmé |
| Journalisation JSON | ✅ Complète | Tous les événements tracés avec IP, horodatage, username |
| Supervision Grafana | ✅ Opérationnelle | Métriques temps réel, logs Loki accessibles |
| Authentification PG | ✅ SCRAM-SHA-256 | Protocole sécurisé confirmé dans les logs |

### Ce qui doit être amélioré

| Lacune | Risque | Priorité |
|---|---|:---:|
| Pas de rate limiting | Brute force possible | Critique |
| Pas de verrouillage de compte | Attaque ciblée possible | Critique |
| Pas de HTTPS | Interception des credentials | Critique |
| Un seul utilisateur DB (admin) | Moindre privilège non respecté | Élevé |
| Pas de log des requêtes SQL | Forensics impossibles | Élevé |
| Pas de sauvegarde des volumes | Perte de données irréversible | Élevé |
| Ports supervision exposés | Accès non autorisé aux métriques | Moyen |
| Pas de restart policy | Indisponibilité en cas de crash | Moyen |
