# Stratégie de sauvegarde et de restauration — HealthPredict AI

**Périmètre :** Base de données PostgreSQL + volumes Docker  
**Date :** Juin 2026

---

## 1. Contexte et enjeux

La base de données PostgreSQL de HealthPredict AI contient des données critiques :
données personnelles des utilisateurs, données de santé et données bancaires.
Toute perte de ces données engagerait la responsabilité légale de l'entreprise
(RGPD article 32 — obligation de garantir l'intégrité et la disponibilité des données)
et causerait un préjudice direct aux personnes concernées.

Actuellement, l'application tourne dans des conteneurs Docker avec un volume non sauvegardé.
Un `docker compose down -v` ou une défaillance disque entraînerait une perte totale
et irréversible des données.

---

## 2. Stratégie — Règle 3-2-1

La stratégie recommandée s'appuie sur la règle **3-2-1**, standard de l'industrie :

- **3** copies des données au minimum
- **2** supports ou emplacements différents
- **1** copie hors site (protection contre sinistre local)

| Copie | Support | Localisation | Fréquence |
|---|---|---|---|
| Copie 1 | Volume Docker | Serveur de production | Données live |
| Copie 2 | Dump pg_dump | Disque local dédié | Quotidien |
| Copie 3 | Archive compressée | Stockage distant (S3 ou équivalent souverain) | Hebdomadaire |

---

## 3. Types de sauvegarde

### 3.1 Sauvegarde logique complète (pg_dump)

La sauvegarde logique exporte le contenu de la base sous forme de fichier SQL
restaurable sur n'importe quelle instance PostgreSQL compatible.

**Commande :**
```bash
docker exec tp3_postgres pg_dump \
  -U admin \
  -d tp3_users \
  --format=custom \
  --compress=9 \
  -f /backup/tp3_users_$(date +%Y%m%d_%H%M%S).dump
```

**Fréquence :** quotidienne, déclenchée à 02h00 (activité minimale)  
**Rétention :** 30 jours  
**Taille estimée :** quelques Mo pour cette base (données de test)

### 3.2 Archivage WAL (Write-Ahead Logging)

Le WAL est le journal de transactions de PostgreSQL. Son archivage permet une
restauration à un point précis dans le temps (PITR — Point In Time Recovery),
ce qui est essentiel pour récupérer l'état de la base juste avant un incident.

**Configuration à ajouter dans `postgresql.conf` :**
```
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'
```

**Fréquence :** continu (chaque segment WAL de 16 Mo archivé automatiquement)  
**Rétention :** 7 jours (suffisant pour couvrir la fenêtre de restauration)

### 3.3 Snapshot de volume Docker

Pour les environnements Docker, une copie du volume peut être réalisée directement.

**Commande :**
```bash
docker run --rm \
  -v tp3_postgres_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/postgres_volume_$(date +%Y%m%d).tar.gz /data
```

**Fréquence :** hebdomadaire  
**Rétention :** 4 semaines

---

## 4. Fréquences et rétention

| Type de sauvegarde | Fréquence | Rétention | Justification |
|---|---|---|---|
| Dump complet quotidien | Chaque nuit à 02h00 | 30 jours | Permet de revenir jusqu'à 1 mois en arrière |
| WAL archiving | Continu | 7 jours | Restauration au point précis avant incident |
| Dump hebdomadaire | Dimanche à 03h00 | 1 an | Conformité légale, audit annuel |
| Snapshot volume | Hebdomadaire | 4 semaines | Restauration rapide de l'environnement complet |

**Justification des 30 jours :** le RGPD n'impose pas de durée de rétention minimale pour
les sauvegardes, mais 30 jours permet de couvrir la plupart des scénarios d'incident
(détection tardive, corruption silencieuse). Au-delà, le coût de stockage augmente sans
bénéfice proportionnel.

---

## 5. Procédure de restauration

### 5.1 Restauration complète (perte totale de la base)

```bash
# 1. Arrêter le backend pour éviter les écritures pendant la restauration
docker compose stop backend

# 2. Créer une nouvelle instance PostgreSQL vide
docker compose up -d db

# 3. Restaurer depuis le dernier dump
docker exec -i tp3_postgres pg_restore \
  -U admin \
  -d tp3_users \
  --clean \
  --if-exists \
  /backup/tp3_users_YYYYMMDD_HHMMSS.dump

# 4. Vérifier l'intégrité des données
docker exec tp3_postgres psql -U admin -d tp3_users \
  -c "SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM sensitive_data;"

# 5. Redémarrer le backend
docker compose start backend
```

### 5.2 Restauration à un point dans le temps (PITR)

Pour revenir à l'état de la base à un instant T (ex: avant une suppression accidentelle) :

```bash
# 1. Arrêter PostgreSQL
docker compose stop db

# 2. Restaurer le dernier dump complet antérieur à T
pg_restore -U admin -d tp3_users /backup/tp3_users_YYYYMMDD.dump

# 3. Rejouer les WAL jusqu'au point souhaité
# Dans recovery.conf (PostgreSQL 12+: postgresql.conf) :
# restore_command = 'cp /backup/wal/%f %p'
# recovery_target_time = '2026-06-10 09:44:00'

# 4. Démarrer PostgreSQL en mode recovery
docker compose start db
```

### 5.3 Restauration partielle (table corrompue)

```bash
# Extraire uniquement la table users depuis un dump complet
pg_restore \
  -U admin \
  -d tp3_users \
  -t users \
  /backup/tp3_users_YYYYMMDD.dump
```

---

## 6. Tests de restauration

Une sauvegarde non testée est une sauvegarde dont on ne peut pas garantir le fonctionnement.
Les tests de restauration doivent être réalisés **sur un environnement distinct**, jamais
en production.

**Procédure de test mensuelle :**

1. Restaurer le dernier dump sur une instance PostgreSQL de test
2. Vérifier le nombre d'enregistrements par table
3. Vérifier la cohérence des données (clés étrangères, contraintes)
4. Vérifier que l'application peut se connecter et fonctionner normalement
5. Consigner le résultat dans le registre des tests de restauration

**Critères de succès :**
- Nombre d'enregistrements identique à la source
- Aucune erreur lors de `pg_restore`
- Application opérationnelle après connexion à la base restaurée
- Durée de restauration inférieure au RTO défini (voir ci-dessous)

---

## 7. Indicateurs clés (RTO et RPO)

| Indicateur | Définition | Objectif recommandé |
|---|---|---|
| **RPO** (Recovery Point Objective) | Perte de données maximale acceptable | 24h (sauvegarde quotidienne) |
| **RTO** (Recovery Time Objective) | Délai maximal de remise en service | 4 heures |

Pour réduire le RPO à moins d'1 heure, activer l'archivage WAL continu.
Pour réduire le RTO, automatiser la procédure de restauration avec un script dédié.
