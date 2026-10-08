"""Small database helper.

Every query in the app goes through query_all / query_one / execute, so the
rest of the codebase never touches a cursor directly.

Two drivers are supported:
  * mysql  - the real deployment target (XAMPP / MySQL 8), via mysql-connector.
  * sqlite - a zero-setup fallback so the app can be demoed on a machine with
             no MySQL server. Same SQL, placeholders are rewritten to "?".

All SQL in this project is written in portable syntax (no NOW(), no DATE_SUB,
no TIMESTAMPDIFF) and timestamps are passed in as Python datetimes, so the
same statements run on both engines.
"""
import sqlite3
import datetime
from decimal import Decimal
from flask import g, current_app

_MYSQL_IMPORT_ERROR = None
try:  # pragma: no cover - depends on the machine
    import mysql.connector
    from mysql.connector import Error as MySQLError
except Exception as exc:  # noqa: BLE001
    mysql = None
    MySQLError = Exception
    _MYSQL_IMPORT_ERROR = exc


class DatabaseUnavailable(RuntimeError):
    """Raised when we cannot reach the database at all."""


def driver():
    return current_app.config["DB_DRIVER"]


def _connect_mysql():
    if mysql is None:
        raise DatabaseUnavailable(
            "mysql-connector-python is not installed. Run "
            "`pip install -r requirements.txt` (original error: %s)" % _MYSQL_IMPORT_ERROR
        )
    cfg = current_app.config
    try:
        return mysql.connector.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            database=cfg["DB_NAME"],
            autocommit=False,
        )
    except MySQLError as exc:
        raise DatabaseUnavailable(
            "Cannot connect to MySQL at %s:%s as '%s'. Is XAMPP/MySQL running and "
            "has database/schema.sql been imported? (%s)"
            % (cfg["DB_HOST"], cfg["DB_PORT"], cfg["DB_USER"], exc)
        ) from exc


def _connect_sqlite():
    path = current_app.config["SQLITE_PATH"]
    conn = sqlite3.connect(path, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conn():
    if "db_conn" not in g:
        g.db_conn = _connect_sqlite() if driver() == "sqlite" else _connect_mysql()
    return g.db_conn


def close_conn(_exc=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def _prepare(sql):
    """SQLite uses ? placeholders; we author everything with %s."""
    if driver() == "sqlite":
        return sql.replace("%s", "?")
    return sql


def _cursor(conn):
    if driver() == "sqlite":
        return conn.cursor()
    return conn.cursor(dictionary=True)


def _normalise(value):
    """MySQL returns DECIMAL columns as Decimal; SQLite returns float.

    Decimal is not JSON-serialisable, so /api/issues (the whole city map) would
    work on SQLite and fail on MySQL. Normalising here means every caller sees
    the same Python types whichever driver is configured.
    """
    if isinstance(value, Decimal):
        return float(value)
    return value


def _rows_to_dicts(cursor, rows):
    return [{k: _normalise(v) for k, v in dict(r).items()} for r in rows]


def query_all(sql, params=()):
    conn = get_conn()
    cur = _cursor(conn)
    try:
        cur.execute(_prepare(sql), tuple(params))
        return _rows_to_dicts(cur, cur.fetchall())
    finally:
        cur.close()


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=(), commit=True):
    """Run an INSERT/UPDATE/DELETE. Returns the new row id (or rowcount)."""
    conn = get_conn()
    cur = _cursor(conn)
    try:
        cur.execute(_prepare(sql), tuple(params))
        new_id = cur.lastrowid
        if commit:
            conn.commit()
        return new_id if new_id else cur.rowcount
    finally:
        cur.close()


def commit():
    get_conn().commit()


def rollback():
    try:
        get_conn().rollback()
    except Exception:  # noqa: BLE001
        pass


def now():
    """One source of truth for timestamps, portable across both engines."""
    return datetime.datetime.now().replace(microsecond=0)


def as_datetime(value):
    """SQLite hands back strings; MySQL hands back datetimes."""
    if value is None or isinstance(value, datetime.datetime):
        return value
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def healthcheck():
    """Returns (ok, message). Used by the friendly setup screen."""
    try:
        query_one("SELECT 1 AS ok")
        return True, "connected"
    except DatabaseUnavailable as exc:
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
