# Rapport de Conformité RGPD, risques cloud et sécurité du système d'information

## Introduction

Ce rapport présente une analyse complète de la sécurité du système d'information de HealthPredict AI. L'objectif est d'identifier les vulnérabilités présentes dans l'architecture, d'évaluer les risques associés selon leur gravité et leur probabilité, et de proposer des mesures de protection concrètes et priorisées.

L'analyse s'appuie sur deux axes complémentaires : d'une part, les tests techniques réalisés sur l'application (démonstration d'injection SQL en TP2, sécurisation en TP3), et d'autre part, l'évaluation de la conformité réglementaire au regard du RGPD et des risques liés à l'hébergement cloud.


## 1. Cartographie des vulnérabilités du système

L'analyse du système a permis d'identifier des vulnérabilités à plusieurs niveaux de l'architecture : applicatif, base de données, infrastructure et organisationnel.

### 1.1 Couche applicative

La vulnérabilité la plus critique identifiée est une **injection SQL** dans le backend Flask. La requête de connexion était construite par concaténation directe de la saisie utilisateur :

```python
# Code vulnérable (TP2)
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

En saisissant `' OR '1'='1` comme nom d'utilisateur, la requête devient logiquement vraie pour tous les enregistrements, accordant un accès sans mot de passe. De même, le payload `admin'--` supprime entièrement la vérification du mot de passe grâce au commentaire SQL `--`.

Cette faille a été confirmée expérimentalement : les six vecteurs d'attaque testés ont tous abouti à une connexion non autorisée ou à une extraction de données.

Par ailleurs, les messages d'erreur renvoyés au client en cas d'exception exposaient la structure interne de la base de données (noms de tables, colonnes), facilitant la reconnaissance du système par un attaquant.

### 1.2 Base de données

Deux problèmes majeurs ont été identifiés au niveau de la base de données PostgreSQL.

En premier lieu, les **mots de passe étaient stockés en clair** dans la table `users`. En cas de fuite de la base, qu'elle soit provoquée par une injection SQL ou par un accès direct, les identifiants de tous les comptes étaient immédiatement exploitables. Les mots de passe récupérés lors des tests comprennent `alice2024`, `Adm1n$uper!`, `Ch@rlie99`, etc.

En second lieu, la table `sensitive_data` contenait des **données bancaires non chiffrées** : numéros de carte (format `4111-1111-1111-XXXX`), soldes de compte (jusqu'à 99 999,99 €) et notes confidentielles. Ces données étaient accessibles via une injection de type `UNION SELECT` sans aucune protection supplémentaire.

### 1.3 Infrastructure et supervision

L'application ne disposait d'**aucun mécanisme de journalisation** des tentatives de connexion. Une attaque pouvait donc se dérouler sur une longue période sans laisser de trace et sans déclencher la moindre alerte.

De même, aucune **limitation du nombre de tentatives** n'était en place, rendant les attaques par force brute ou par dictionnaire tout à fait envisageables sans risque de blocage.

Les communications entre le frontend et le backend ne transitaient pas par HTTPS, exposant les identifiants saisis à une interception sur le réseau.

### 1.4 Niveau organisationnel et réglementaire

Sur le plan de la conformité RGPD, plusieurs manquements ont été identifiés. L'entreprise ne dispose pas de registre des traitements au sens de l'article 30 du RGPD, document pourtant obligatoire pour toute organisation traitant des données personnelles. Aucune Analyse d'Impact relative à la Protection des Données (AIPD) n'a été réalisée pour les traitements portant sur des données de santé, alors que celles-ci sont classées comme données sensibles au sens de l'article 9 du RGPD.

Enfin, l'hébergement des données sur AWS, infrastructure soumise au droit américain (Cloud Act), crée un conflit potentiel avec les exigences du RGPD européen. Les autorités américaines peuvent légalement exiger l'accès aux données hébergées par des entreprises américaines, y compris sur des serveurs localisés en Europe, sans nécessairement en informer les personnes concernées ni le responsable de traitement.


## 2. Liste des risques identifiés

### Risques liés aux accès non autorisés

**R1 — Injection SQL permettant le contournement de l'authentification**  
Un attaquant peut se connecter à n'importe quel compte, y compris les comptes administrateurs, sans connaître le moindre mot de passe. Ce vecteur d'attaque a été démontré avec les payloads `' OR '1'='1`, `admin'--` et `' OR 1=1--`, tous couronnés de succès sur l'application non sécurisée.

**R2 — Absence de verrouillage de compte**  
Sans limite sur le nombre de tentatives de connexion, un attaquant peut tester des milliers de combinaisons d'identifiants et de mots de passe de façon automatisée sans jamais être bloqué.

**R3 — Permissions base de données trop larges**  
L'utilisateur applicatif dispose d'un accès complet à toutes les tables, sans restriction par rôle ou par périmètre de données. En cas de compromission de l'application, l'attaquant hérite de tous ces droits.

### Risques liés aux fuites de données

**R4 — Extraction de la base entière par injection SQL**  
Via une injection de type `UNION SELECT`, l'ensemble des données utilisateurs (identifiants, mots de passe, emails, rôles) et des données sensibles (numéros de carte bancaire, soldes) peuvent être extraites en une seule requête.

**R5 — Mots de passe en clair exploitables immédiatement**  
En l'absence de hachage, toute fuite de la base de données expose directement les mots de passe. Ces derniers sont souvent réutilisés par les utilisateurs sur d'autres services, ce qui amplifie considérablement l'impact d'une telle fuite.

**R6 — Données bancaires non chiffrées**  
Les numéros de carte et les soldes sont stockés en clair dans la table `sensitive_data`. Une fuite de ces informations expose l'entreprise à des sanctions lourdes (RGPD, DSP2) et engage sa responsabilité civile et pénale.

**R7 — Exposition des données via les messages d'erreur**  
Les traces d'erreur PostgreSQL renvoyées au client révèlent la structure de la base (noms de tables, colonnes, types), informations précieuses pour un attaquant souhaitant affiner ses payloads.

**R8 — Transfert de données vers AWS (Cloud Act)**  
Les données personnelles et de santé hébergées sur AWS peuvent faire l'objet d'une injonction des autorités américaines sans notification préalable, en violation des principes du RGPD.

### Risques liés aux pertes de données

**R9 — Absence de politique de sauvegarde documentée**  
Aucune procédure de backup n'a été identifiée. En cas de défaillance matérielle ou d'attaque destructive (ex. ransomware), la restauration des données ne serait pas garantie.

**R10 — Absence de politique de rétention**  
Les données sont conservées indéfiniment sans règle de purge, ce qui augmente l'exposition en cas de fuite et constitue un manquement au principe de minimisation du RGPD.

### Risques liés aux mauvaises configurations

**R11 — Communications non chiffrées (absence de HTTPS)**  
Les identifiants de connexion transitent en clair entre le navigateur de l'utilisateur et le serveur. Une interception sur le réseau (attaque de type man-in-the-middle) suffit à les récupérer.

**R12 — Absence de supervision et d'alertes**  
Sans système de monitoring, les attaques en cours ne sont pas détectées. L'équipe ne peut pas réagir en temps réel ni constituer de preuves a posteriori pour une éventuelle enquête.


## 3. Matrice des risques

La criticité de chaque risque est calculée en multipliant sa probabilité d'occurrence par sa gravité potentielle, sur une échelle de 1 à 5.

| Risque | Probabilité | Gravité | Criticité | Niveau |
|---|:---:|:---:|:---:|:---:|
| Injection SQL → extraction de la base | 5 | 5 | 25 | **Critique** |
| Contournement d'authentification (admin) | 5 | 5 | 25 | **Critique** |
| Fuite des données bancaires | 4 | 5 | 20 | **Critique** |
| Mots de passe en clair exploitables | 4 | 5 | 20 | **Critique** |
| Absence de journalisation → attaque non détectée | 4 | 4 | 16 | **Élevé** |
| Accès Cloud Act aux données de santé | 3 | 5 | 15 | **Élevé** |
| Erreurs SQL exposées → reconnaissance | 4 | 3 | 12 | **Élevé** |
| Brute force sans verrouillage | 3 | 4 | 12 | **Élevé** |
| Absence de HTTPS → interception | 3 | 4 | 12 | **Élevé** |
| Permissions DB trop larges | 3 | 4 | 12 | **Élevé** |
| Absence de registre RGPD (art. 30) | 2 | 4 | 8 | **Moyen** |
| Données de santé sans AIPD | 2 | 4 | 8 | **Moyen** |
| Absence de politique de rétention | 2 | 3 | 6 | **Moyen** |
| Absence de politique de sauvegarde | 2 | 3 | 6 | **Moyen** |

**Légende :**
- **Critique** (≥ 20) : risque majeur exigeant une correction immédiate
- **Élevé** (10–19) : action prioritaire à mettre en œuvre sous un mois
- **Moyen** (5–9) : à planifier dans les trois mois
- **Faible** (< 5) : à surveiller, traitement différable


## 4. Recommandations de sécurité

### Priorité 1 — Mesures critiques (à appliquer immédiatement)

**Utiliser des requêtes préparées pour toutes les interactions avec la base de données**

C'est la correction fondamentale contre les injections SQL. En transmettant les paramètres séparément de la requête, il est impossible pour une valeur saisie par l'utilisateur de modifier la logique SQL, quelle que soit sa forme.

```python
# Méthode sécurisée
cur.execute("SELECT * FROM users WHERE username = %s", (username,))
```

Cette mesure a été mise en œuvre dans le TP3 et a neutralisé l'ensemble des six vecteurs d'attaque testés.

**Hacher les mots de passe avec bcrypt avant stockage**

Même en cas de fuite complète de la base de données, les mots de passe hachés avec bcrypt restent inutilisables. L'algorithme est intentionnellement lent, ce qui rend les attaques par force brute coûteuses en temps. Le sel généré automatiquement à chaque hachage rend de plus les tables arc-en-ciel inefficaces.

**Ne jamais renvoyer les détails des erreurs techniques au client**

En cas d'exception, le serveur doit retourner un message générique. La trace technique doit être enregistrée côté serveur uniquement, dans les logs applicatifs.

### Priorité 2 — Mesures élevées (sous un mois)

**Mettre en place une journalisation structurée de tous les événements d'authentification**

Chaque tentative de connexion, qu'elle soit réussie ou échouée, doit être enregistrée avec horodatage, identifiant utilisateur, adresse IP et résultat. Un format JSON structuré facilite l'exploitation automatique des logs par des outils de supervision. Cette mesure a été implémentée dans le TP3, avec une table `auth_log` en base et un fichier de log JSON lu par Promtail.

**Déployer une supervision avec Grafana, Prometheus et Loki**

Le tableau de bord mis en place dans le TP3 permet de détecter en temps réel les comportements anormaux : pic de connexions échouées, ratio échecs/succès supérieur à 10:1, adresse IP concentrant un grand nombre de tentatives. Sans supervision, une attaque peut durer des heures sans être remarquée.

**Limiter le nombre de tentatives de connexion par adresse IP**

Une règle de rate limiting (par exemple cinq tentatives par IP sur dix minutes) stoppe efficacement les attaques automatisées. Cette mesure est complémentaire de la journalisation car elle agit en prévention là où les logs agissent en détection.

**Implémenter le verrouillage temporaire de compte**

Après un nombre défini d'échecs consécutifs (par exemple dix tentatives), le compte doit être temporairement verrouillé. Cela protège contre les attaques ciblées sur un compte précis.

**Déployer HTTPS sur l'ensemble des communications**

L'utilisation d'un certificat TLS est indispensable pour chiffrer les identifiants en transit. Sans HTTPS, une simple capture réseau suffit à récupérer les mots de passe saisis par les utilisateurs.

### Priorité 3 — Mesures organisationnelles et réglementaires (sous trois mois)

**Appliquer le principe du moindre privilège pour les accès base de données**

L'utilisateur applicatif ne doit avoir accès qu'aux tables et aux opérations strictement nécessaires à son fonctionnement. Un compte dédié en lecture seule pour les requêtes de consultation, distinct du compte d'administration, réduit considérablement l'impact d'une compromission.

**Chiffrer les données sensibles au repos**

Les numéros de carte bancaire et les données de santé doivent être chiffrés au niveau applicatif avant d'être stockés en base. Même en cas d'accès direct à la base de données, les données restent illisibles sans la clé de chiffrement.

**Activer l'authentification à deux facteurs pour les comptes administrateurs**

Un second facteur d'authentification (TOTP, clé matérielle) protège les comptes les plus sensibles même si le mot de passe est compromis.

**Rédiger le registre des traitements (article 30 RGPD)**

Ce document est une obligation légale pour toute organisation traitant des données personnelles. Il doit recenser l'ensemble des traitements, leurs finalités, les catégories de données concernées, les durées de conservation et les mesures de sécurité associées.

**Réaliser une AIPD pour les données de santé**

L'article 35 du RGPD impose une Analyse d'Impact relative à la Protection des Données pour tout traitement susceptible d'engendrer un risque élevé pour les personnes. Les données de santé entrent explicitement dans cette catégorie.

**Évaluer une solution d'hébergement souverain ou vérifier la certification DPF d'AWS**

Pour résoudre le conflit entre les exigences du Cloud Act américain et du RGPD européen, deux options sont envisageables : migrer vers un hébergeur européen soumis uniquement au droit de l'UE, ou vérifier qu'AWS est certifié dans le cadre du Data Privacy Framework (DPF) et contractualiser des clauses contractuelles types (CCT).

**Définir une politique de rétention et de purge des données**

Les données ne doivent pas être conservées au-delà de leur durée d'utilité. Une politique documentée précisant les durées de rétention par catégorie de données et les procédures de purge associées est nécessaire pour respecter le principe de minimisation du RGPD.

## 5. Synthèse et tableau de conformité RGPD

| Section | Élément analysé | Détails | Risque | Statut |
|---|---|---|---|---|
| **Traitements** | RH & Paie | Gestion administrative, salaires, données de santé | Moyen | Sécuriser l'accès aux données de santé |
| | Relation Client | Identité, historique achats, support | Faible | Minimiser les données stockées |
| | Marketing | Profilage, cookies, prospection email | Élevé | Recueillir un consentement explicite |
| **Conformité** | Finalité | Usage limité aux objectifs déclarés | Conforme | Maintenir la veille sur les usages |
| | Minimisation | Collecte limitée au strict nécessaire | À optimiser | Purger les données inutiles |
| | Données sensibles | Protection des données de santé (RH) | Point d'attention | Réaliser une AIPD dédiée |
| **Cloud Act** | Transferts US | Dépendance aux hébergeurs américains | Critique | Vérifier certification DPF |
| | Juridiction | Conflit entre lois US et RGPD européen | Critique | Envisager le chiffrement local |
| | Espionnage | Accès administratif étranger non notifié | Élevé | Évaluer des solutions souveraines |
| **Matrice risques** | Données clients | Fuite de l'historique d'achat / profilage | Élevé | Renforcer le chiffrement CRM |
| | Non-conformité US | Sanctions liées aux transferts hors UE | Critique | Contractualiser les CCT |
| | Défaut registre | Absence de documentation légale obligatoire | Moyen | Rédiger le registre art. 30 |
| **Actions** | Registre | Absence de registre officiel des traitements | Obligatoire | Création immédiate du registre |
| | Information | Défaut de transparence sur les transferts | Obligatoire | Mise à jour des mentions légales |
| | Conservation | Manque de politique de purge des données | Important | Définir les durées de rétention |

## Conclusion

L'analyse menée sur le système d'information de HealthPredict AI a révélé des vulnérabilités graves, dont certaines ont été confirmées expérimentalement. L'injection SQL identifiée en TP2 permettait à un attaquant de contourner entièrement l'authentification et d'accéder à l'ensemble des données de la base, y compris les données bancaires et les mots de passe.

Les corrections apportées en TP3 : requêtes préparées, hachage bcrypt, journalisation structurée et supervision Grafana ont neutralisé les risques les plus critiques. Cependant, plusieurs mesures restent à mettre en œuvre pour atteindre un niveau de sécurité satisfaisant en production : HTTPS, rate limiting, verrouillage de compte, chiffrement des données sensibles au repos et mise en conformité RGPD complète.

La sécurité d'un système ne repose pas uniquement sur la correction des failles techniques. Elle exige également une démarche organisationnelle continue : documentation des traitements, formation des équipes, veille réglementaire et audits réguliers. C'est cette combinaison de mesures techniques et organisationnelles qui permet de réduire durablement le niveau de risque.
