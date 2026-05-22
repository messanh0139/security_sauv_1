import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Fonction pour obtenir une connexion à la base de données
def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME", "tp2_users"),
        user=os.environ.get("DB_USER", "admin"),
        password=os.environ.get("DB_PASSWORD", "admin123"),
    )


# Route pour vérifier que le serveur fonctionne
@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "Backend opérationnel"})


# Route de connexion, volontairement vulnérable à l'injection SQL
@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "message": "Champs manquants"}), 400

    # Mauvaise pratique : on concatène directement les entrées utilisateur dans la requête
    # Cela permet à un attaquant de modifier la logique SQL
    query = (
        f"SELECT id, username, password, email, role "
        f"FROM   users "
        f"WHERE  username = '{username}' "
        f"AND    password = '{password}'"
    )

    print("Requête SQL exécutée :")
    print(query, flush=True)

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        results = [dict(zip(cols, row)) for row in rows]

        if results:
            user = results[0]
            return jsonify({
                "success": True,
                "message": f"Bienvenue, {user['username']} !",
                "user": {
                    "id":       user["id"],
                    "username": user["username"],
                    "email":    user["email"],
                    "role":     user["role"],
                },
                # On renvoie toutes les lignes pour montrer ce que l'injection peut exposer
                "allRows": results,
            })
        else:
            return jsonify({
                "success": False,
                "message": "Identifiant ou mot de passe incorrect",
            }), 401

    except Exception as e:
        print(f"Erreur SQL : {e}", flush=True)
        # On expose l'erreur pour que l'étudiant puisse comprendre ce qui se passe
        return jsonify({
            "success": False,
            "message": "Erreur SQL",
            "error":   str(e),
            "query":   query,
        }), 500


# Route pour récupérer le profil d'un utilisateur avec ses données sensibles
@app.route("/api/profile/<int:user_id>")
def profile(user_id):
    query = (
        f"SELECT u.username, u.email, u.role, "
        f"       s.card_number, s.balance, s.secret_note "
        f"FROM   users u "
        f"LEFT JOIN sensitive_data s ON s.user_id = u.id "
        f"WHERE  u.id = {user_id}"
    )
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(query)
        row  = cur.fetchone()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        if row:
            return jsonify({"success": True, "data": dict(zip(cols, row))})
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Route pour lister tous les utilisateurs
@app.route("/api/users")
def users():
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id")
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return jsonify({"success": True, "users": [dict(zip(cols, r)) for r in rows]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Backend Flask démarré sur le port {port}")
    print("Attention : ce serveur est volontairement vulnérable, usage pédagogique uniquement")
    app.run(host="0.0.0.0", port=port, debug=False)
