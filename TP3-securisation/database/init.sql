-- Schéma TP3 — les données sont insérées par le backend (mots de passe hachés)

CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(100)  NOT NULL UNIQUE,
    password   VARCHAR(255)  NOT NULL,
    email      VARCHAR(255)  NOT NULL,
    role       VARCHAR(50)   NOT NULL DEFAULT 'user',
    created_at TIMESTAMP     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sensitive_data (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) UNIQUE,
    card_number VARCHAR(20),
    balance     NUMERIC(12,2),
    secret_note TEXT
);

-- Table d'audit des événements d'authentification
CREATE TABLE IF NOT EXISTS auth_log (
    id         SERIAL PRIMARY KEY,
    event      VARCHAR(50)  NOT NULL,
    username   VARCHAR(100),
    success    BOOLEAN      NOT NULL,
    ip_address VARCHAR(45),
    details    TEXT,
    created_at TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_log_created_at ON auth_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_log_username   ON auth_log(username);
