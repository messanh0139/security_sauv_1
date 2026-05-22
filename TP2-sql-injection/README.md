# Analyse de sécurité - TP2 Injection SQL

## Lancer l'application

```bash
cd TP2-sql-injection
docker-compose up -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:8080 |
| Backend API | http://localhost:3000 |
| Health check | http://localhost:3000/health |
| Liste des utilisateurs | http://localhost:3000/api/users |

Pour lancer les tests d'injection :

```bash
source venv/bin/activate
python test_injection.py
```

## 1. Quelle est la vulnérabilité exploitée ?

La vulnérabilité exploitée est une injection SQL. Elle se produit quand une application
construit une requête SQL en collant directement ce que l'utilisateur a tapé, sans
vérifier ni nettoyer les données reçues.

Dans notre application, la requête de connexion ressemble à ça :

```sql
SELECT * FROM users WHERE username = 'alice' AND password = 'alice2024'
```

Si on tape à la place `' OR 1=1--` comme nom d'utilisateur, la requête devient :

```sql
SELECT * FROM users WHERE username = '' OR 1=1-- AND password = 'x'
```

La condition `1=1` est toujours vraie, et le `--` met en commentaire tout ce qui suit,
donc le mot de passe n'est plus vérifié du tout. L'attaquant est connecté.


## 2. Pourquoi l'application accepte une connexion invalide ?

Parce que la requête SQL est construite par concaténation de chaînes. L'application
fait confiance à ce que l'utilisateur envoie et l'intègre directement dans la requête
sans aucun contrôle.

Quand on injecte `admin'--` comme nom d'utilisateur, la logique du `AND password = ...`
est purement et simplement supprimée par le commentaire SQL `--`. L'application reçoit
une ligne de résultat, considère que la connexion est valide, et laisse passer
l'utilisateur.

En résumé, ce n'est pas un bug d'authentification, c'est un bug de construction de
requête qui casse la logique d'authentification.


## 3. Quelles données peuvent être compromises ?

Avec cette faille, un attaquant peut récupérer :

- les noms d'utilisateurs et leurs mots de passe en clair
- les adresses email
- les rôles des comptes (user, admin)
- potentiellement toutes les autres tables de la base si l'injection est plus poussée
  (via UNION SELECT par exemple)

Dans notre lab, on voit concrètement que les mots de passe de tous les utilisateurs
s'affichent dès qu'on utilise un payload basique comme `' OR 1=1--`. Aucune donnée
de la table users n'est protégée.


## 4. Cette faille vient-elle de la base de données ou de l'application ?

Elle vient de l'application, pas de la base de données. PostgreSQL fonctionne
exactement comme prévu : il exécute la requête qu'on lui envoie. Le problème est
que l'application lui envoie une mauvaise requête, construite à partir d'entrées
utilisateur non contrôlées.

La base de données ne peut pas deviner qu'une partie de la requête vient d'un
utilisateur malveillant. Elle reçoit du SQL valide et l'exécute.

La correction doit donc se faire côté application, en utilisant des requêtes
paramétrées (prepared statements) qui séparent le code SQL des données :

```python
cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
```

Avec cette approche, peu importe ce que l'utilisateur tape, ça ne peut jamais
modifier la structure de la requête.


## 5. Quels sont les risques pour une entreprise ?

Les conséquences peuvent être très lourdes selon le contexte :

**Fuite de données** : toute la base peut être extraite, y compris des informations
personnelles, des coordonnées bancaires, des données médicales ou des secrets
commerciaux.

**Contournement d'authentification** : n'importe qui peut se connecter en tant
qu'administrateur sans connaître le moindre mot de passe.

**Destruction de données** : avec les bons droits, un attaquant peut supprimer ou
modifier des tables entières.

**Impact légal** : en Europe, une fuite de données personnelles oblige l'entreprise
à notifier la CNIL sous 72 heures. Les sanctions peuvent atteindre 4% du chiffre
d'affaires annuel mondial (RGPD).

**Impact réputationnel** : une fuite rendue publique entraîne une perte de confiance
des clients difficile à récupérer, surtout si les mots de passe étaient stockés en
clair comme dans notre exemple.

Une injection SQL reste aujourd'hui l'une des failles les plus répandues et les plus
dangereuses. Elle figure chaque année dans le top 3 de l'OWASP (Open Web Application
Security Project).
