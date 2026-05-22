-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(100) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    email      VARCHAR(255) NOT NULL,
    role       VARCHAR(50)  NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table des données sensibles liées à chaque utilisateur
CREATE TABLE IF NOT EXISTS sensitive_data (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    card_number VARCHAR(20),
    balance     NUMERIC(12,2),
    secret_note TEXT
);

-- Insertion des utilisateurs de test
INSERT INTO users (username, password, email, role) VALUES
    ('alice',   'alice2024',   'alice@company.com',   'user'),
    ('bob',     'b0bSecure!',  'bob@company.com',     'user'),
    ('charlie', 'Ch@rlie99',   'charlie@company.com', 'user'),
    ('admin',   'Adm1n$uper!', 'admin@company.com',   'admin'),
    ('diana',   'diana_pass',  'diana@company.com',   'user')
ON CONFLICT (username) DO NOTHING;

-- Insertion des données sensibles associées
INSERT INTO sensitive_data (user_id, card_number, balance, secret_note)
SELECT id, '4111-1111-1111-1001', 15420.50, 'Compte courant principal'
FROM users WHERE username = 'alice';

INSERT INTO sensitive_data (user_id, card_number, balance, secret_note)
SELECT id, '4111-1111-1111-1002', 8250.00, 'Épargne vacances'
FROM users WHERE username = 'bob';

INSERT INTO sensitive_data (user_id, card_number, balance, secret_note)
SELECT id, '4111-1111-1111-1003', 3100.75, 'Compte professionnel'
FROM users WHERE username = 'charlie';

INSERT INTO sensitive_data (user_id, card_number, balance, secret_note)
SELECT id, '4111-1111-1111-9999', 99999.99, 'COMPTE ADMINISTRATEUR - CONFIDENTIEL'
FROM users WHERE username = 'admin';

INSERT INTO sensitive_data (user_id, card_number, balance, secret_note)
SELECT id, '4111-1111-1111-1005', 5670.30, 'Investissements'
FROM users WHERE username = 'diana';
