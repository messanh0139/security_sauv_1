# Plan d'amélioration et feuille de route — HealthPredict AI

**Date :** Juin 2026  
**Basé sur :** Audit TP4, vulnérabilités identifiées en TP2, mesures déployées en TP3

---

## 1. État des lieux

### Ce qui a été accompli (TP2 - TP3)

| Mesure | Impact | Statut |
|---|---|:---:|
| Requêtes SQL préparées | Élimine les injections SQL | Fait |
| Hachage bcrypt des mots de passe | Protège les credentials en cas de fuite DB | Fait |
| Messages d'erreur génériques | Empêche la reconnaissance de la base | Fait |
| Journalisation JSON structurée | Traçabilité complète des accès | Fait |
| Supervision Grafana + Prometheus | Détection des attaques en temps réel | Fait |
| Logs Loki avec filtres par événement | Forensics et analyse a posteriori | Fait |
| Table `auth_log` en base | Audit trail persistant des authentifications | Fait |

### Ce qui reste à faire

| Lacune | Risque actuel | Priorité |
|---|---|:---:|
| Absence de HTTPS | Credentials interceptables sur le réseau | Critique |
| Pas de rate limiting | Brute force illimité possible | Critique |
| Pas de verrouillage de compte | Attaque ciblée sur un compte | Critique |
| Données bancaires en clair | Fuite exploitable immédiatement | Élevé |
| Un seul rôle DB (admin) | Moindre privilège non respecté | Élevé |
| Pas de log SQL | Forensics incomplets | Élevé |
| Pas de sauvegarde automatisée | Perte de données irréversible possible | Élevé |
| Ports supervision exposés | Accès non autorisé aux métriques internes | Moyen |
| Pas de 2FA admin | Compte admin compromettable | Moyen |
| Pas de registre RGPD | Non-conformité légale | Moyen |
| Pas d'AIPD données santé | Non-conformité RGPD art. 35 | Moyen |

---

## 2. Feuille de route

### Phase 1 — Corrections critiques (Semaines 1-2)

**Objectif :** éliminer les risques qui permettraient une compromission immédiate en production.

#### Action 1.1 — Déployer HTTPS avec TLS

```yaml
# Ajout dans docker-compose.yml
nginx:
  image: nginx:alpine
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./certs:/etc/nginx/certs
  ports:
    - "443:443"
  depends_on:
    - backend
```

**Justification :** sans HTTPS, les mots de passe transitent en clair sur le réseau.
Une capture avec Wireshark suffit à les récupérer.

#### Action 1.2 — Implémenter le rate limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)

@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per 10 minutes")
def login():
    ...
```

**Justification :** stoppe les attaques automatisées. Les 6 injections du TP2 ont été
envoyées en 716 ms — un rate limiting à 5/10 min aurait bloqué à la 5ème tentative.

#### Action 1.3 — Verrouillage de compte après N échecs

```python
# Dans la logique de login
failures = get_recent_failures(username, window_minutes=15)
if failures >= 10:
    log_event("ACCOUNT_LOCKED", username, False, ip)
    return jsonify({"success": False, "message": "Compte temporairement verrouillé"}), 429
```

**Justification :** protège contre les attaques ciblées sur un compte précis,
complémentaire du rate limiting (qui agit sur l'IP, pas sur le compte).

---

### Phase 2 — Renforcement (Semaines 3-6)

**Objectif :** éliminer les risques élevés identifiés à l'audit.

#### Action 2.1 — Chiffrement des données sensibles au repos

Les colonnes `card_number` et `balance` de la table `sensitive_data` doivent être
chiffrées avant stockage avec une clé gérée séparément de la base.

```python
from cryptography.fernet import Fernet

# Chiffrement avant INSERT
fernet = Fernet(os.environ["ENCRYPTION_KEY"])
encrypted_card = fernet.encrypt(card_number.encode()).decode()

# Déchiffrement après SELECT
decrypted_card = fernet.decrypt(encrypted_card.encode()).decode()
```

#### Action 2.2 — Principe du moindre privilège sur la base de données

```sql
-- Créer un utilisateur dédié à l'application avec droits limités
CREATE USER app_user WITH PASSWORD 'mot_de_passe_fort';
GRANT SELECT, INSERT ON users TO app_user;
GRANT SELECT, INSERT ON sensitive_data TO app_user;
GRANT INSERT ON auth_log TO app_user;
-- Pas de DROP, ALTER, DELETE, TRUNCATE
```

#### Action 2.3 — Activer le log des requêtes SQL

```
# Dans postgresql.conf
log_statement = 'mod'          # log INSERT, UPDATE, DELETE
log_min_duration_statement = 1000  # log les requêtes > 1 seconde
```

#### Action 2.4 — Automatiser les sauvegardes

```bash
#!/bin/bash
# /etc/cron.d/pg_backup — exécuté chaque nuit à 02h00
BACKUP_DIR=/var/backups/postgres
DATE=$(date +%Y%m%d_%H%M%S)

docker exec tp3_postgres pg_dump \
  -U admin -d tp3_users \
  --format=custom --compress=9 \
  > "$BACKUP_DIR/tp3_users_$DATE.dump"

# Supprimer les sauvegardes de plus de 30 jours
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete
```

---

### Phase 3 — Conformité et gouvernance (Mois 2-3)

**Objectif :** atteindre la conformité RGPD et mettre en place la gouvernance documentée.

#### Action 3.1 — Rédiger le registre des traitements (art. 30 RGPD)

Document obligatoire recensant pour chaque traitement :
- La finalité
- Les catégories de données et de personnes concernées
- Les destinataires
- Les transferts hors UE et leurs garanties
- Les durées de conservation
- Les mesures de sécurité

#### Action 3.2 — Réaliser l'AIPD pour les données de santé

Obligatoire avant tout traitement à risque élevé (art. 35 RGPD).
Doit être menée avec le DPO et valider que les mesures de protection sont proportionnées.

#### Action 3.3 — Activer le 2FA pour les comptes administrateurs

```python
# Avec pyotp (TOTP — compatible Google Authenticator)
import pyotp

totp = pyotp.TOTP(user.totp_secret)
if not totp.verify(token_from_user):
    return jsonify({"success": False, "message": "Code 2FA invalide"}), 401
```

#### Action 3.4 — Vérifier la certification DPF d'AWS

Contrôler que l'instance AWS utilisée est couverte par le Data Privacy Framework
et intégrer des clauses contractuelles types (CCT) dans le contrat de sous-traitance.

---

### Phase 4 — Amélioration continue (Long terme)

**Objectif :** passer d'une sécurité réactive à une sécurité proactive.

| Action | Fréquence | Responsable |
|---|---|---|
| Test d'intrusion externe (pentest) | Annuel | RSSI + prestataire externe |
| Scan de vulnérabilités (OWASP ZAP, Trivy) | Mensuel | Équipe dev |
| Formation sécurité (OWASP Top 10) | Annuel | Tous les développeurs |
| Revue des droits d'accès | Trimestriel | Data Steward |
| Test de restauration des sauvegardes | Mensuel | RSSI |
| Mise à jour des dépendances | Hebdomadaire | Équipe dev |
| Revue du tableau de bord Grafana | Continue | RSSI |

---

## 3. Tableau de priorisation synthétique

| # | Action | Effort | Impact | Priorité |
|---|---|:---:|:---:|:---:|
| 1.1 | HTTPS / TLS | Moyen | Critique | **P1** |
| 1.2 | Rate limiting | Faible | Critique | **P1** |
| 1.3 | Verrouillage de compte | Faible | Critique | **P1** |
| 2.1 | Chiffrement données bancaires | Élevé | Élevé | **P2** |
| 2.2 | Moindre privilège DB | Faible | Élevé | **P2** |
| 2.3 | Log des requêtes SQL | Faible | Élevé | **P2** |
| 2.4 | Sauvegarde automatisée | Moyen | Élevé | **P2** |
| 3.1 | Registre RGPD art. 30 | Moyen | Moyen | **P3** |
| 3.2 | AIPD données de santé | Élevé | Moyen | **P3** |
| 3.3 | 2FA comptes admin | Moyen | Moyen | **P3** |
| 3.4 | Vérification DPF AWS | Faible | Moyen | **P3** |
| 4.x | Pentest annuel | Élevé | Long terme | **P4** |
