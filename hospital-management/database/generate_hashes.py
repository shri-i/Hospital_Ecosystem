"""
Generate werkzeug password hashes for the seed users.

Usage:
    python database/generate_hashes.py               -> hashes for the demo passwords
    python database/generate_hashes.py mySecret123   -> hash for any password

Copy the printed hash into seed.sql, or run the printed UPDATE in MySQL Workbench.
"""
import sys
from werkzeug.security import generate_password_hash

DEMO_USERS = {
    'admin': 'admin123',
    'dr.mehta': 'doctor123',
    'reception': 'recep123',
}

if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(generate_password_hash(sys.argv[1]))
    else:
        for username, password in DEMO_USERS.items():
            h = generate_password_hash(password)
            print(f"-- {username} / {password}")
            print(f"UPDATE users SET password_hash = '{h}' WHERE username = '{username}';\n")
