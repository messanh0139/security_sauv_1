"""
TP3 — Tests de l'application sécurisée
On vérifie que les connexions légitimes passent, que les mauvais mots de passe
sont rejetés, et que Prometheus a bien compté les tentatives.
"""

import requests

BASE_URL = "http://localhost:3001"

RESET = "\033[0m"
ROUGE = "\033[91m"
VERT  = "\033[92m"
JAUNE = "\033[93m"
GRAS  = "\033[1m"


def section(texte):
    print(f"\n{GRAS}{texte}{RESET}")
    print("-" * 60)


def test_login(label, username, password, expect_success=True):
    res  = requests.post(f"{BASE_URL}/api/login", json={"username": username, "password": password})
    data = res.json()
    ok   = data.get("success", False)

    if ok == expect_success:
        couleur = VERT
        verdict = "PASS"
    else:
        couleur = ROUGE
        verdict = "FAIL"

    statut = "ACCORDEE" if ok else "REFUSEE"
    print(f"  [{couleur}{verdict}{RESET}] {label}")
    print(f"         username={username!r}  password={password!r}")
    print(f"         => {statut}  — {data.get('message', '')}")

    if ok:
        u = data.get("user", {})
        print(f"         user : id={u.get('id')}  role={u.get('role')}")


section("1. Santé du serveur")
try:
    health = requests.get(f"{BASE_URL}/health").json()
    print(f"  {VERT}OK{RESET} — {health.get('message')}")
except Exception as exc:
    print(f"  {ROUGE}ERREUR{RESET} — serveur inaccessible : {exc}")
    exit(1)

section("2. Utilisateurs enregistrés (mots de passe masqués)")
users = requests.get(f"{BASE_URL}/api/users").json().get("users", [])
for u in users:
    print(f"  {u['id']}  {u['username']:<12}  {u['email']:<28}  {u['role']}")

section("3. Vérification du hachage bcrypt")
print("  Le hash bcrypt commence par $2b$ et contient le sel intégré.")
print("  Chaque hash est unique même pour le même mot de passe.")
print()
print("  Pour vérifier directement dans PostgreSQL :")
print("    docker exec -it tp3_postgres psql -U admin -d tp3_users")
print("    SELECT username, LEFT(password, 30) || '...' AS hash_prefix FROM users;")

section("4. Connexions valides — doivent réussir")
test_login("alice  / alice2024",   "alice",   "alice2024",   expect_success=True)
test_login("bob    / b0bSecure!",  "bob",     "b0bSecure!",  expect_success=True)
test_login("admin  / Adm1n$uper!", "admin",   "Adm1n$uper!", expect_success=True)
test_login("charlie/ Ch@rlie99",   "charlie", "Ch@rlie99",   expect_success=True)
test_login("diana  / diana_pass",  "diana",   "diana_pass",  expect_success=True)

section("5. Connexions invalides — doivent être refusées")
test_login("mauvais mot de passe",      "alice",   "mauvais_mdp",    expect_success=False)
test_login("utilisateur inexistant",    "inexistant", "password",     expect_success=False)
test_login("mot de passe vide",         "alice",   "",               expect_success=False)
test_login("mot de passe en clair TP2", "alice",   "alice2024wrong", expect_success=False)

section("6. Métriques Prometheus")
try:
    metrics = requests.get(f"{BASE_URL}/metrics").text
    lines = [l for l in metrics.splitlines() if "login_attempts_total" in l and not l.startswith("#")]
    if lines:
        print("  Compteurs login_attempts_total :")
        for line in lines:
            print(f"    {VERT}{line}{RESET}")
    else:
        print(f"  {JAUNE}Aucune métrique login_attempts_total encore (lancez des connexions){RESET}")
except Exception as exc:
    print(f"  {ROUGE}Métriques inaccessibles : {exc}{RESET}")

print(f"\n{GRAS}Tests terminés. Consultez les logs : docker logs tp3_backend{RESET}\n")
