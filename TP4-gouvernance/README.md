# TP4 — Gouvernance, audit et stratégie de sécurisation

Suite du TP3 (sécurisation + supervision). Ce TP réalise un audit global de l'application
et de la base de données, définit une politique de gouvernance, une stratégie de sauvegarde
et propose une feuille de route d'amélioration continue.

---

## Documents produits

| Fichier | Contenu |
|---|---|
| `rapport_audit.md` | Audit des logs PostgreSQL, Docker et applicatifs |
| `politique_gouvernance.md` | Rôles, règles de gestion et protection des données |
| `strategie_sauvegarde.md` | Plan de sauvegarde, restauration et fréquences |
| `plan_amelioration.md` | Feuille de route priorisée |
| `support_soutenance.md` | Synthèse pour la présentation finale |

---

## Questions d'analyse

### Q1 — Les mesures de sécurité mises en place sont-elles suffisantes ?

Les mesures déployées en TP3 (requêtes préparées, bcrypt, journalisation, Grafana) couvrent
les risques les plus critiques identifiés en TP2. Elles sont nécessaires mais pas suffisantes
pour une mise en production réelle. Plusieurs axes restent ouverts : absence de HTTPS, pas de
rate limiting, pas de verrouillage de compte, données bancaires non chiffrées au repos,
absence de registre RGPD. La sécurité est un processus continu, pas un état final.

### Q2 — Quels indicateurs permettent d'évaluer la sécurité de l'application ?

**Indicateurs techniques (Grafana / Prometheus) :**
- Taux d'échec des connexions : `login_attempts_total{status="failure"}`
- Ratio échecs/succès sur 1 heure : alerte si > 3:1
- Nombre de connexions PostgreSQL actives : pic anormal = attaque possible
- Débit de tentatives par minute : `rate(login_attempts_total[1m])`

**Indicateurs qualitatifs :**
- Présence de payloads d'injection dans les logs (guillemets, OR, UNION, --)
- IP concentrant un grand nombre de tentatives
- Tentatives sur des comptes inexistants (énumération)
- Délai moyen de détection d'une attaque (MTTD)
- Délai moyen de réponse à un incident (MTTR)

### Q3 — Pourquoi l'audit est-il essentiel dans une démarche de gouvernance ?

L'audit permet de vérifier que les mesures de sécurité fonctionnent effectivement, pas
seulement qu'elles existent. Une politique de sécurité sans audit est une déclaration
d'intention, pas une garantie. L'audit remplit trois fonctions :

1. **Vérification** : les contrôles mis en place produisent bien l'effet attendu
2. **Détection** : les comportements anormaux sont identifiés et tracés
3. **Conformité** : les obligations légales (RGPD art. 5.2 — accountability) sont respectées

Dans notre cas, l'audit des logs a permis de confirmer que les 6 tentatives d'injection SQL
ont toutes été bloquées (401) et correctement enregistrées, ce qui valide l'efficacité des
mesures déployées.

### Q4 — Quelle stratégie de sauvegarde recommanderiez-vous ?

Une stratégie en trois niveaux basée sur la règle **3-2-1** :
- **3** copies des données
- **2** supports différents (disque local + stockage distant)
- **1** copie hors site (cloud ou site secondaire)

Pour une base PostgreSQL de cette nature :
- Sauvegarde complète hebdomadaire (pg_dump)
- Sauvegarde incrémentale quotidienne (WAL archiving)
- Rétention 30 jours pour les sauvegardes quotidiennes, 1 an pour les hebdomadaires
- Test de restauration mensuel obligatoire

### Q5 — Quelles actions proposeriez-vous pour améliorer la sécurité et la conformité ?

**Court terme (immédiat) :**
- Déployer HTTPS avec un certificat TLS
- Implémenter le rate limiting (5 tentatives / IP / 10 min)
- Verrouillage automatique de compte après 10 échecs

**Moyen terme (1-3 mois) :**
- Chiffrer les données bancaires au repos (AES-256)
- Appliquer le principe du moindre privilège sur les accès DB
- Activer le 2FA pour les comptes administrateurs
- Rédiger le registre des traitements RGPD (art. 30)

**Long terme (3-6 mois) :**
- Réaliser une AIPD pour les données de santé
- Évaluer un hébergement souverain européen
- Mettre en place un programme de tests d'intrusion annuels
- Former les équipes à la sécurité (OWASP Top 10)
