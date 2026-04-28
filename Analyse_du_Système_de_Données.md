## Analyse du Système de Données de HealthPredict AI 

Ce document présente une analyse du système de données de HealthPredict AI. 

L'objectif est de cartographier les flux, classifier les données, identifier les acteurs, évaluer la conformité au RGPD 

### 1. Schéma des flux de données  

Cette partie consiste à illustrer le parcours des données au sein de l'écosystème HealthPredict AI. 
Nous mettons en évidence les interactions entre l'utilisateur, l'application web, l'API backend, le modèle de machine learning, le stockage AWS S3 et le dashboard interne.  

##### Flux identifiés

| Source      | Destination       | Données                             |
| ----------- | ----------------- | ----------------------------------- |
| Utilisateur | Application web   | nom, email, âge                     |
| Utilisateur | Questionnaire     | symptômes, historique médical       |
| Frontend    | API backend       | données saisies                     |
| API         | AWS S3            | stockage brut                       |
| API         | Modèle IA         | données d’entraînement / prédiction |
| API         | Dashboard interne | résultats, profils, statistiques    |
| Utilisateur | Serveurs          | IP, logs, navigation                |


voir le schéma des flux en fichier .png



### 2. Classification des données 


| Catégorie de données | Exemples de données collectées | Niveau de sensibilité | Justification de la collecte | Impact en cas de fuite |
| --- | --- | --- | --- | --- |
| **Données personnelles** | Nom, email, âge | Standard | Identification de l'utilisateur, communication, personnalisation des services | Atteinte à la vie privée, usurpation d'identité |
| **Données de santé (Sensibles)** | Symptômes, historique médical | Très Élevé | Base du modèle de prédiction des risques de maladies | Discrimination, stigmatisation, chantage, atteinte à la réputation |
| **Données techniques** | Logs, adresse IP, navigation | Standard | Sécurité du système, analyse d'usage, amélioration de l'application | Suivi des activités, attaque ciblée | 



### 3. Identification des acteurs du traitement 

| Rôle | Entité | Responsabilités principales | Implications RGPD |
| --- | --- | --- | --- |
| **Responsable du traitement** | **HealthPredict AI** | Détermine les finalités et les moyens du traitement des données. Est responsable de la conformité globale au RGPD, de la sécurité des données, de la gestion des consentements et des droits des personnes concernées | Doit s'assurer que tous les traitements sont licites, loyaux et transparents |
| **Sous-traitant (Hébergement & Stockage)** | **AWS S3** | Fournit l'infrastructure de stockage des données | Doit offrir des garanties suffisantes quant à la mise en œuvre de mesures techniques et organisationnelles appropriées |