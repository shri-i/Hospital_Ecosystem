"""
db.py - small helper around mysql-connector-python.

* One connection per web request (stored in flask.g, closed automatically).
* autocommit is ON, so single INSERT/UPDATE statements are saved at once.
* For multi-step work use `with transaction() as cur:` which runs
  START TRANSACTION ... COMMIT, or ROLLBACK if anything fails.
* Every query uses %s placeholders (parameterized) -> no SQL injection.
"""
from contextlib import contextmanager

import mysql.connector
from flask import g

from config import DB_CONFIG


def get_db():
    """Return the connection for this request, creating it if needed."""
    if 'db' not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
        g.db.autocommit = True
    return g.db


def close_db(e=None):
    """Called by Flask at the end of every request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query(sql, params=(), one=False):
    """Run a SELECT and return rows as dictionaries (or one row if one=True)."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, params=()):
    """Run a single INSERT / UPDATE / DELETE. Returns the new row id for INSERTs."""
    cur = get_db().cursor()
    cur.execute(sql, params)
    new_id = cur.lastrowid
    cur.close()
    return new_id


@contextmanager
def transaction():
    """
    Usage:
        with transaction() as cur:
            cur.execute("INSERT ...", (...))
            cur.execute("UPDATE ...", (...))
    All statements are committed together, or all rolled back on error.
    """
    db = get_db()
    db.start_transaction()
    cur = db.cursor(dictionary=True)
    try:
        yield cur
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
