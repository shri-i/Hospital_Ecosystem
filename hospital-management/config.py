"""
config.py - database credentials and app settings.
Edit DB_PASSWORD to match YOUR MySQL root password
(or set the environment variables instead).
"""
import os

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'port':     int(os.environ.get('DB_PORT', 3306)),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'shri@1234'),
    'database': os.environ.get('DB_NAME', 'hospital_db'),
}

# Used by Flask to sign the session cookie. Change it for anything public.
SECRET_KEY = os.environ.get('SECRET_KEY', 'hms-dev-secret-key-change-me')
