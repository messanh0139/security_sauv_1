import os
import logging
import json
from datetime import datetime
import psycopg2
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import bcrypt
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
CORS(app)

# On distingue success / failure / error parce que "failure" c'est un mauvais mdp,
# "error" c'est un crash côté serveur — pas la même chose à surveiller dans Grafana.
login_attempts = Counter(
    "login_attempts_total",
    "Nombre total de tentatives de connexion",
    ["status"],
)
active_sessions = Gauge(
    "active_sessions",
    "Sessions actives simulées",
)

os.makedirs("/app/logs", exist_ok=True)

logger = logging.getLogger("tp3")
logger.setLevel(logging.INFO)

file_handler   = logging.FileHandler("/app/logs/app.log")
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def log_event(event: str, username: str, success: bool, ip: str, details: str = ""):
    # JSON pour que Promtail/Loki puisse filtrer par champ sans regex fragile
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event":     event,
        "username":  username,
        "success":   success,
        "ip":        ip,
        "details":   details,
    }
    logger.info(json.dumps(record, ensure_ascii=False))


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME", "tp3_users"),
        user=os.environ.get("DB_USER", "admin"),
        password=os.environ.get("DB_PASSWORD", "admin123"),
    )


def init_db():
    users_to_seed = [
        ("alice",   "alice2024",   "alice@company.com",   "user"),
        ("bob",     "b0bSecure!",  "bob@company.com",     "user"),
        ("charlie", "Ch@rlie99",   "charlie@company.com", "user"),
        ("admin",   "Adm1n$uper!", "admin@company.com",   "admin"),
        ("diana",   "diana_pass",  "diana@company.com",   "user"),
    ]
    sensitive_to_seed = [
        ("alice",   "4111-1111-1111-1001", 15420.50, "Compte courant principal"),
        ("bob",     "4111-1111-1111-1002",  8250.00, "Épargne vacances"),
        ("charlie", "4111-1111-1111-1003",  3100.75, "Compte professionnel"),
        ("admin",   "4111-1111-1111-9999", 99999.99, "COMPTE ADMINISTRATEUR - CONFIDENTIEL"),
        ("diana",   "4111-1111-1111-1005",  5670.30, "Investissements"),
    ]
    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] > 0:
            cur.close()
            conn.close()
            logger.info(json.dumps({"event": "DB_INIT", "details": "already seeded"}))
            return

        # bcrypt.gensalt() génère un sel différent à chaque appel,
        # donc deux utilisateurs avec le même mot de passe auront des hashes différents.
        # C'est ce qui rend les rainbow tables inutiles.
        for username, plain_pwd, email, role in users_to_seed:
            hashed = bcrypt.hashpw(plain_pwd.encode(), bcrypt.gensalt()).decode()
            cur.execute(
                "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                (username, hashed, email, role),
            )

        for username, card, balance, note in sensitive_to_seed:
            cur.execute(
                """
                INSERT INTO sensitive_data (user_id, card_number, balance, secret_note)
                SELECT id, %s, %s, %s FROM users WHERE username = %s
                """,
                (card, balance, note, username),
            )

        conn.commit()
        cur.close()
        conn.close()
        logger.info(json.dumps({"event": "DB_INIT", "details": "seeded with bcrypt hashes"}))

    except Exception as exc:
        logger.error(json.dumps({"event": "DB_INIT_ERROR", "details": str(exc)}))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "Backend sécurisé opérationnel"})


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "")
    ip       = request.remote_addr

    if not username or not password:
        return jsonify({"success": False, "message": "Champs manquants"}), 400

    try:
        conn = get_connection()
        cur  = conn.cursor()

        # En TP2 on concaténait directement username dans la chaîne SQL — c'est ce qui
        # permettait à "' OR '1'='1" de modifier la logique de la requête.
        # Ici le %s est un emplacement réservé : psycopg2 envoie la valeur séparément
        # au moteur PostgreSQL, qui la traite comme une donnée et jamais comme du code.
        cur.execute(
            "SELECT id, username, password, email, role FROM users WHERE username = %s",
            (username,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            user_id, db_username, db_hash, email, role = row
            # checkpw relit le sel depuis le hash stocké, donc pas besoin de le
            # conserver séparément. C'est le sel qui fait que brute-forcer la BDD
            # entière d'un coup ne marche pas.
            if bcrypt.checkpw(password.encode(), db_hash.encode()):
                login_attempts.labels(status="success").inc()
                active_sessions.inc()
                log_event("LOGIN_SUCCESS", username, True, ip)
                return jsonify({
                    "success": True,
                    "message": f"Bienvenue, {db_username} !",
                    "user": {
                        "id":       user_id,
                        "username": db_username,
                        "email":    email,
                        "role":     role,
                    },
                })

        login_attempts.labels(status="failure").inc()
        log_event("LOGIN_FAILURE", username, False, ip, "invalid credentials")
        # Même message que "user inexistant" : on ne veut pas indiquer à un attaquant
        # si le compte existe ou non.
        return jsonify({"success": False, "message": "Identifiant ou mot de passe incorrect"}), 401

    except Exception as exc:
        login_attempts.labels(status="error").inc()
        log_event("LOGIN_ERROR", username, False, ip, str(exc))
        # On ne renvoie pas str(exc) au client — une stack trace PostgreSQL peut
        # révéler la structure de la table, ce qu'on a vu en TP2.
        return jsonify({"success": False, "message": "Erreur interne du serveur"}), 500


@app.route("/api/logout", methods=["POST"])
def logout():
    active_sessions.dec()
    return jsonify({"success": True})


@app.route("/api/profile/<int:user_id>")
def profile(user_id):
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT u.username, u.email, u.role,
                   s.card_number, s.balance, s.secret_note
            FROM   users u
            LEFT JOIN sensitive_data s ON s.user_id = u.id
            WHERE  u.id = %s
            """,
            (user_id,),
        )
        row  = cur.fetchone()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        if row:
            return jsonify({"success": True, "data": dict(zip(cols, row))})
        return jsonify({"success": False, "message": "Utilisateur introuvable"}), 404

    except Exception as exc:
        logger.error(json.dumps({"event": "PROFILE_ERROR", "details": str(exc)}))
        return jsonify({"success": False, "message": "Erreur interne"}), 500


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
    except Exception as exc:
        logger.error(json.dumps({"event": "USERS_ERROR", "details": str(exc)}))
        return jsonify({"success": False, "message": "Erreur interne"}), 500


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 3001))
    logger.info(json.dumps({"event": "SERVER_START", "port": port}))
    app.run(host="0.0.0.0", port=port, debug=False)
