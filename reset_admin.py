import sqlite3
from werkzeug.security import generate_password_hash

DB = "database/civicpulse.sqlite3"

email = "admin@civicpulse.com"
password = "Admin@123"

conn = sqlite3.connect(DB)
cursor = conn.cursor()

password_hash = generate_password_hash(
    password,
    method="pbkdf2:sha256"
)

cursor.execute(
    "SELECT id FROM users WHERE email = ?",
    (email,)
)

existing = cursor.fetchone()

if existing:
    cursor.execute(
        "UPDATE users SET password_hash = ?, role = 'admin' WHERE email = ?",
        (password_hash, email)
    )
    print("Existing admin account reset.")
else:
    cursor.execute(
        """INSERT INTO users
        (name, email, password_hash, role, impact_score, created_at)
        VALUES (?, ?, ?, 'admin', 0, datetime('now'))""",
        ("CivicPulse Admin", email, password_hash)
    )
    print("New admin account created.")

conn.commit()
conn.close()

print()
print("Admin Email: admin@civicpulse.com")
print("Admin Password: Admin@123")