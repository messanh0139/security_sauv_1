# Support de soutenance — Projet fil rouge HealthPredict AI

**Titre :** Sécurisation, gouvernance et supervision d'une application web  
**Date :** Juin 2026

---

## Slide 1 — Présentation du projet

**HealthPredict AI** est une application web d'authentification manipulant des données
personnelles, de santé et bancaires.

Le projet fil rouge s'est déroulé en 4 travaux pratiques progressifs :

| TP | Titre | Objectif |
|---|---|---|
| TP1 | Cartographie des données | Identifier les flux, les acteurs, la conformité RGPD |
| TP2 | Injection SQL | Démontrer et comprendre la vulnérabilité |
| TP3 | Sécurisation + supervision | Corriger les failles, mettre en place Grafana |
| TP4 | Gouvernance + audit | Auditer, gouverner, planifier l'amélioration continue |

---

## Slide 2 — TP1 : Cartographie des données

**Système analysé :** HealthPredict AI — flux de données entre l'utilisateur,
le frontend, l'API backend, le modèle IA, le stockage AWS S3 et le dashboard interne.

**Classification des données :**

| Catégorie | Niveau de sensibilité | Impact en cas de fuite |
|---|:---:|---|
| Données personnelles (nom, email) | Standard | Usurpation d'identité |
| Données de santé | Très élevé | Discrimination, chantage |
| Données techniques (logs, IP) | Standard | Attaque ciblée |

**Enjeu principal :** données de santé = données sensibles au sens RGPD (art. 9), protection renforcée obligatoire et AIPD requise.

---

## Slide 3 — TP2 : La faille SQL Injection

**Vulnérabilité :** construction de requêtes SQL par concaténation directe.

```python
# Code vulnérable
query = f"SELECT * FROM users WHERE username = '{username}'"
```

**Démonstration :**

| Payload | Requête résultante | Résultat |
|---|---|---|
| `' OR '1'='1` | `WHERE username = '' OR '1'='1'` | Tous les comptes exposés |
| `admin'--` | `WHERE username = 'admin'--` | Admin sans mot de passe |
| `' UNION SELECT ...` | Requête sur toutes les tables | Extraction complète de la BDD |

**Données compromises :** 5 comptes, mots de passe en clair, numéros de carte bancaire,
soldes financiers, rôles (admin inclus).

---

## Slide 4 — TP3 : Sécurisation de l'application

**Deux corrections fondamentales :**

1. **Requêtes préparées** — le paramètre est transmis séparément, jamais interprété comme du code SQL
```python
cur.execute("SELECT * FROM users WHERE username = %s", (username,))
```

2. **Hachage bcrypt** — mot de passe illisible même en cas de fuite de la base
```
alice2024  ->  $2b$12$xK7pL3mN9qR2vW8tY1uZ4e...
```

**Résultat :** les 6 vecteurs d'attaque du TP2 -> tous bloqués (401 Unauthorized).

---

## Slide 5 — TP3 : Stack de supervision

**Architecture de supervision déployée :**

```
Flask -> /metrics -> Prometheus -> Grafana (métriques)
Flask -> app.log  -> Promtail  -> Loki    -> Grafana (logs)
PostgreSQL       -> pg_exporter -> Prometheus
```

**Dashboard Grafana — ce qu'on observe en temps réel :**

- Compteurs connexions réussies / échouées
- Graphe de débit des tentatives (rate / minute)
- Logs filtrés `LOGIN_FAILURE` avec payloads visibles
- Connexions PostgreSQL actives

**Données de l'audit :** 11 succès, 11 échecs dont 6 injections SQL —
toutes détectées, tracées et bloquées.

---

## Slide 6 — TP4 : Audit des logs

**Logs applicatifs analysés (10 juin 2026) :**

```json
{"event": "LOGIN_FAILURE", "username": "' UNION SELECT 1,'hacker'...", "ip": "172.21.0.1"}
{"event": "LOGIN_FAILURE", "username": "' OR 1=1--", "ip": "172.21.0.1"}
```

**Constats de l'audit :**

Toutes les attaques bloquées et journalisées  
Authentification PostgreSQL via SCRAM-SHA-256  
Aucune erreur serveur (taux d'erreur = 0)  
Attaque automatisée détectée (6 payloads en 716 ms)  
Pas de rate limiting -> attaque non interrompue  
Un seul utilisateur DB — moindre privilège non respecté  

---

## Slide 7 — TP4 : Gouvernance des données

**Rôles définis :**

| Rôle | Responsabilité principale |
|---|---|
| Responsable du traitement | Conformité RGPD globale, notification CNIL |
| DPO | Conseil, contrôle, point de contact CNIL |
| RSSI | Sécurité technique, incidents, audits |
| Data Owner | Validation des accès, durées de rétention |
| Data Steward | Droits des personnes, qualité des données |

**Règles clés :**
- Minimisation : ne collecter que le nécessaire
- Chiffrement obligatoire pour les données sensibles
- Revue des droits d'accès tous les 3 mois
- Notification CNIL en cas de violation sous 72 heures

---

## Slide 8 — TP4 : Stratégie de sauvegarde

**Règle 3-2-1 appliquée :**

```
Données live  ->  Dump quotidien (02h00)  ->  Archive hebdomadaire (S3)
   [Copie 1]        [Copie 2 — local]          [Copie 3 — hors site]
```

**RPO / RTO :**

| Indicateur | Valeur cible | Signification |
|---|---|---|
| RPO | 24 heures | Perte de données maximale acceptable |
| RTO | 4 heures | Délai de remise en service maximum |

**Point critique :** les tests de restauration sont **obligatoires** mensuellement.
Une sauvegarde non testée ne garantit rien.

---

## Slide 9 — Plan d'amélioration

**Feuille de route en 4 phases :**

```
Phase 1 (Sem 1-2)  : HTTPS + Rate limiting + Verrouillage compte
Phase 2 (Sem 3-6)  : Chiffrement données + Moindre privilège DB + Sauvegardes auto
Phase 3 (Mois 2-3) : Registre RGPD + AIPD + 2FA admin + DPF AWS
Phase 4 (Long terme): Pentest annuel + Formation + Amélioration continue
```

**Principe directeur :** la sécurité n'est pas un état final, c'est un processus.
Chaque mesure réduit la surface d'attaque mais n'élimine pas tous les risques.
L'audit régulier et la supervision continue permettent de maintenir le niveau
de protection dans le temps.

---

## Slide 10 — Conclusion

**Ce que ce projet démontre :**

1. Une seule vulnérabilité (injection SQL) suffit à compromettre l'ensemble d'un système
2. Les corrections techniques (requêtes préparées, bcrypt) sont efficaces et rapides à mettre en œuvre
3. La sécurisation ne s'arrête pas au code : supervision, gouvernance et conformité sont indissociables
4. L'audit valide que les mesures fonctionnent réellement, pas seulement qu'elles existent

**Les trois piliers d'une sécurité durable :**

| Technique | Organisationnel | Réglementaire |
|---|---|---|
| Requêtes préparées | Gouvernance | RGPD art. 30 |
| bcrypt | Rôles définis | AIPD |
| HTTPS | Procédures audit | Notification CNIL |
| Rate limiting | Formation | DPF / CCT |
| Supervision | Tests restauration | Registre traitements |
