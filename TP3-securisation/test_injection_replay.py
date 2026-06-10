"""
TP3 — Rejeu des injections SQL du TP2

En TP2, la requête était construite par concaténation de chaînes :
    WHERE username = '{username}' AND password = '{password}'
Un payload comme "' OR '1'='1" cassait la structure SQL et accordait l'accès.

Ici on rejoue les mêmes attaques contre le backend sécurisé (port 3001).
Toutes doivent retourner 401 — si l'une réussit, la sécurisation est insuffisante.
"""

import requests

BASE_URL_TP3 = "http://localhost:3001"

RESET = "\033[0m"
ROUGE = "\033[91m"
VERT  = "\033[92m"
JAUNE = "\033[93m"
GRAS  = "\033[1m"


def section(texte):
    print(f"\n{GRAS}{texte}{RESET}")
    print("-" * 60)


def replay(label, username, password, tp2_result_description):
    res  = requests.post(f"{BASE_URL_TP3}/api/login", json={"username": username, "password": password})
    data = res.json()
    ok   = data.get("success", False)

    verdict = f"{ROUGE}INJECTION REUSSIE (GRAVE){RESET}" if ok else f"{VERT}NEUTRALISEE{RESET}"

    print(f"\n  Attaque : {label}")
    print(f"    payload  : username={username!r}  password={password!r}")
    print(f"    TP2      : {JAUNE}{tp2_result_description}{RESET}")
    print(f"    TP3      : {verdict}  — {data.get('message', '')}")
    if ok:
        print(f"    {ROUGE}ALERTE : l'injection a fonctionné, la sécurisation est insuffisante !{RESET}")


section("Vérification du backend TP3")
try:
    h = requests.get(f"{BASE_URL_TP3}/health").json()
    print(f"  {VERT}OK{RESET} — {h.get('message')}")
except Exception as exc:
    print(f"  {ROUGE}Backend TP3 inaccessible : {exc}{RESET}")
    print("  Lancez d'abord : docker compose up -d")
    exit(1)

section("Rejeu des injections SQL (tous les vecteurs du TP2)")

replay(
    label="Bypass total — OR 1=1",
    username="' OR '1'='1",
    password="' OR '1'='1",
    tp2_result_description="ACCORDEE — 5 comptes exposés, mots de passe en clair retournés",
)

replay(
    label="Commentaire SQL sur admin",
    username="admin'--",
    password="nimporte",
    tp2_result_description="ACCORDEE — compte admin obtenu sans mot de passe",
)

replay(
    label="OR 1=1 avec commentaire",
    username="' OR 1=1--",
    password="x",
    tp2_result_description="ACCORDEE — toutes les lignes de la table retournées",
)

replay(
    label="UNION injection (tentative d'exfiltration)",
    username="' UNION SELECT 1,'hacker','hash',4,'admin'--",
    password="x",
    tp2_result_description="Potentiellement accordée selon la structure de la table",
)

replay(
    label="Injection dans le mot de passe uniquement",
    username="alice",
    password="' OR '1'='1",
    tp2_result_description="ACCORDEE — condition sur le mot de passe contournée",
)

replay(
    label="Guillemet simple seul (test basique)",
    username="'",
    password="x",
    tp2_result_description="Erreur SQL exposée (500) — révèle la structure de la requête",
)

section("Analyse — pourquoi les injections échouent")
print("""
  TP2 (VULNÉRABLE) :
    query = f"... WHERE username = '{username}' AND password = '{password}'"
    => Le payload est concaténé tel quel dans la chaîne SQL.
    => "' OR '1'='1" brise la structure et ajoute une condition toujours vraie.

  TP3 (SÉCURISÉ) :
    cur.execute("... WHERE username = %s", (username,))
    => Le driver psycopg2 envoie le paramètre séparément du texte SQL.
    => PostgreSQL reçoit deux éléments distincts :
         • Le plan de requête compilé (immuable)
         • La valeur littérale (jamais interprétée comme SQL)
    => "' OR '1'='1" est cherché comme un nom d'utilisateur réel → introuvable → 401.

  HACHAGE BCRYPT :
    Même si un attaquant lisait la base de données, les mots de passe
    hachés (format $2b$12$...) sont inutilisables sans la valeur originale.
    Le sel intégré au hash empêche les attaques par table arc-en-ciel.
""")
