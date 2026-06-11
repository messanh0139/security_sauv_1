# Politique de gouvernance des données — HealthPredict AI

**Version :** 1.0  
**Date :** Juin 2026  
**Périmètre :** Système d'information HealthPredict AI

---

## 1. Objectifs

La gouvernance des données vise à encadrer la façon dont les données sont collectées,
stockées, utilisées, protégées et supprimées au sein de l'organisation. Elle garantit
que les données sont traitées de manière conforme, sécurisée et alignée avec les
objectifs métier.

Pour HealthPredict AI, trois enjeux sont particulièrement critiques :

- La protection des données de santé, classées comme données sensibles au sens de
  l'article 9 du RGPD
- La conformité aux obligations légales européennes dans un contexte d'hébergement
  cloud américain (Cloud Act)
- La traçabilité des accès et des traitements pour satisfaire aux exigences
  d'accountability (article 5.2 RGPD)

---

## 2. Identification des rôles

### 2.1 Responsable du traitement

**Entité :** HealthPredict AI  
**Responsabilités :**
- Définir les finalités et les moyens du traitement des données
- S'assurer de la conformité globale au RGPD
- Rendre compte des traitements (principle d'accountability)
- Notifier la CNIL en cas de violation de données sous 72 heures

### 2.2 Délégué à la Protection des Données (DPO)

**Rôle :** Conseiller indépendant sur la protection des données  
**Responsabilités :**
- Informer et conseiller l'organisation sur ses obligations RGPD
- Contrôler le respect du règlement en interne
- Coopérer avec la CNIL et servir de point de contact
- Superviser les AIPD pour les traitements à risque élevé

**Obligation de désignation :** oui, car HealthPredict AI traite des données de santé
à grande échelle (article 37 RGPD).

### 2.3 Responsable de la Sécurité des Systèmes d'Information (RSSI)

**Rôle :** Garant de la sécurité technique du système d'information  
**Responsabilités :**
- Définir et mettre en œuvre la politique de sécurité
- Superviser les audits de sécurité et les tests d'intrusion
- Gérer les incidents de sécurité (détection, réponse, documentation)
- Maintenir le système de supervision (Grafana, Prometheus, alertes)
- Former les équipes aux bonnes pratiques de sécurité

### 2.4 Data Owner (Propriétaire de la donnée)

**Rôle :** Responsable métier d'un périmètre de données  
**Exemples chez HealthPredict AI :**
- Directeur médical -> données de santé des patients
- Directeur RH -> données du personnel
- Directeur commercial -> données clients et marketing

**Responsabilités :**
- Valider les règles d'accès à ses données
- Approuver les demandes d'accès inhabituelles
- Définir les durées de rétention adaptées au contexte métier

### 2.5 Data Steward (Intendant de la donnée)

**Rôle :** Garant opérationnel de la qualité et de la conformité des données  
**Responsabilités :**
- Appliquer les règles définies par le Data Owner
- Maintenir le catalogue et le registre des traitements à jour
- Gérer les demandes d'exercice des droits (accès, rectification, effacement)
- Signaler les anomalies ou incohérences dans les données

### 2.6 Équipe de développement

**Responsabilités :**
- Appliquer les principes de security by design et privacy by design
- Utiliser des requêtes préparées, valider les entrées, hacher les mots de passe
- Ne jamais stocker de secrets en dur dans le code ou les fichiers de configuration
- Soumettre le code à des revues de sécurité avant mise en production

---

## 3. Classification des données

| Catégorie | Exemples | Niveau | Mesures obligatoires |
|---|---|:---:|---|
| **Données publiques** | Contenu marketing, documentation | Public | Aucune mesure particulière |
| **Données internes** | Logs techniques, métriques Prometheus | Interne | Accès restreint aux équipes |
| **Données personnelles** | Nom, email, IP, identifiant | Confidentiel | Chiffrement, accès contrôlé, DCP |
| **Données sensibles** | Données de santé, données bancaires | Secret | Chiffrement fort, AIPD, accès strictement limité |

---

## 4. Règles de gestion des données

### 4.1 Collecte

- Ne collecter que les données strictement nécessaires à la finalité déclarée
  (principe de minimisation, article 5 RGPD)
- Obtenir le consentement explicite avant toute collecte de données de santé
- Informer les utilisateurs de la nature des données collectées, de leur finalité
  et de leurs droits (article 13 RGPD)

### 4.2 Stockage

- Chiffrer les données sensibles au repos (AES-256 minimum)
- Hacher les mots de passe avec bcrypt (coût ≥ 12) ou argon2id
- Ne jamais stocker de numéros de carte bancaire complets (conformité PCI-DSS)
- Isoler les données de santé dans un périmètre dédié avec accès restreint

### 4.3 Accès

- Appliquer le principe du moindre privilège : chaque acteur accède uniquement
  aux données nécessaires à sa mission
- Authentification forte (mot de passe + 2FA) obligatoire pour les accès aux
  données sensibles et aux comptes administrateurs
- Revue trimestrielle des droits d'accès pour détecter les accès obsolètes

### 4.4 Transfert

- Toutes les communications doivent être chiffrées via TLS 1.2 minimum
- Les transferts de données hors UE nécessitent des garanties appropriées
  (clauses contractuelles types, certification DPF pour AWS)
- Pas de transmission de données sensibles par email non chiffré

### 4.5 Conservation et suppression

| Catégorie | Durée de conservation | Procédure de suppression |
|---|---|---|
| Données de santé actives | Durée du suivi médical | Anonymisation ou suppression sécurisée |
| Logs d'authentification | 12 mois | Suppression automatique par rotation |
| Données clients inactifs | 3 ans après dernière activité | Suppression sur demande ou automatique |
| Données RH | Durée du contrat + 5 ans | Archivage légal puis destruction |
| Sauvegardes | 30 jours (quotidiennes), 1 an (hebdomadaires) | Écrasement automatique |

---

## 5. Gestion des droits des personnes

Conformément au RGPD, toute personne dont les données sont traitées dispose des droits suivants :

| Droit | Délai de réponse | Responsable |
|---|:---:|---|
| Droit d'accès (art. 15) | 1 mois | Data Steward |
| Droit de rectification (art. 16) | 1 mois | Data Steward |
| Droit à l'effacement (art. 17) | 1 mois | Data Steward + RSSI |
| Droit à la portabilité (art. 20) | 1 mois | Data Steward |
| Droit d'opposition (art. 21) | Immédiat | Data Owner |

---

## 6. Gestion des incidents

En cas de violation de données personnelles, la procédure suivante s'applique :

1. **Détection** (H+0) : le RSSI est alerté via Grafana ou signalement interne
2. **Qualification** (H+2) : évaluation de la nature, du périmètre et de la gravité
3. **Notification CNIL** (H+72 max) : obligatoire si risque pour les personnes concernées
4. **Notification des personnes** : si risque élevé, notification directe sans délai injustifié
5. **Documentation** : tout incident doit être consigné dans le registre des violations
   (article 33.5 RGPD), même s'il n'est pas notifié à la CNIL

---

## 7. Audit et amélioration continue

- Audit interne des accès et des logs : **mensuel**
- Revue des droits utilisateurs : **trimestrielle**
- Test de restauration des sauvegardes : **mensuel**
- Test d'intrusion externe : **annuel**
- Mise à jour de la politique de gouvernance : **annuelle ou après tout incident majeur**
- Formation sécurité de l'ensemble du personnel : **annuelle**
