"""Small database helper.

Every query in the app goes through query_all / query_one / execute, so the
rest of the codebase never touches a cursor directly.

Two drivers are supported:
  * mysql  - the real deployment target (Aiven / XAMPP / MySQL 8),
             via mysql-connector.
  * sqlite - a zero-setup fallback so the app can be demoed locally.

All SQL in this project is written in portable syntax (no NOW(), no DATE_SUB,
no TIMESTAMPDIFF) and timestamps are passed in as Python datetimes, so the
same statements run on both engines.
"""

import sqlite3
import datetime
from decimal import Decimal
from flask import g, current_app

_MYSQL_IMPORT_ERROR = None

try:
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
    """Connect to MySQL/Aiven using the configured environment variables."""

    if mysql is None:
        raise DatabaseUnavailable(
            "mysql-connector-python is not installed. Run "
            "`pip install -r requirements.txt` "
            "(original error: %s)" % _MYSQL_IMPORT_ERROR
        )

    cfg = current_app.config

    try:
        return mysql.connector.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            database=cfg["DB_NAME"],

            # Aiven requires SSL connections.
            # Certificate verification is disabled here because the
            # deployment does not currently provide a CA certificate.
            ssl_verify_cert=False,

            autocommit=False,
        )

    except MySQLError as exc:
        raise DatabaseUnavailable(
            "Cannot connect to MySQL at %s:%s as '%s'. "
            "Check the database credentials, Aiven service status, "
            "SSL configuration, and database name. (%s)"
            % (
                cfg["DB_HOST"],
                cfg["DB_PORT"],
                cfg["DB_USER"],
                exc,
            )
        ) from exc


def _connect_sqlite():
    """Connect to the local SQLite database."""

    path = current_app.config["SQLITE_PATH"]

    conn = sqlite3.connect(
        path,
        detect_types=0,
    )

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def get_conn():
    """Return the current request's database connection."""

    if "db_conn" not in g:
        if driver() == "sqlite":
            g.db_conn = _connect_sqlite()
        else:
            g.db_conn = _connect_mysql()

    return g.db_conn


def close_conn(_exc=None):
    """Close the current database connection."""

    conn = g.pop("db_conn", None)

    if conn is not None:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass


def _prepare(sql):
    """SQLite uses ? placeholders; MySQL uses %s."""

    if driver() == "sqlite":
        return sql.replace("%s", "?")

    return sql


def _cursor(conn):
    """Return a compatible cursor for the selected database."""

    if driver() == "sqlite":
        return conn.cursor()

    return conn.cursor(dictionary=True)


def _normalise(value):
    """Normalise database values for consistent application behaviour.

    MySQL returns DECIMAL columns as Decimal while SQLite returns floats.
    Decimal is not JSON serialisable, so convert it to float.
    """

    if isinstance(value, Decimal):
        return float(value)

    return value


def _rows_to_dicts(cursor, rows):
    """Convert database rows into normal Python dictionaries."""

    return [
        {
            key: _normalise(value)
            for key, value in dict(row).items()
        }
        for row in rows
    ]


def query_all(sql, params=()):
    """Execute a SELECT query and return all rows as dictionaries."""

    conn = get_conn()
    cur = _cursor(conn)

    try:
        cur.execute(
            _prepare(sql),
            tuple(params),
        )

        return _rows_to_dicts(
            cur,
            cur.fetchall(),
        )

    finally:
        cur.close()


def query_one(sql, params=()):
    """Execute a SELECT query and return the first row."""

    rows = query_all(sql, params)

    return rows[0] if rows else None


def execute(sql, params=(), commit=True):
    """Run INSERT/UPDATE/DELETE.

    Returns the new row ID when available, otherwise the affected row count.
    """

    conn = get_conn()
    cur = _cursor(conn)

    try:
        cur.execute(
            _prepare(sql),
            tuple(params),
        )

        new_id = cur.lastrowid

        if commit:
            conn.commit()

        return new_id if new_id else cur.rowcount

    finally:
        cur.close()


def commit():
    """Commit the current transaction."""

    get_conn().commit()


def rollback():
    """Rollback the current transaction."""

    try:
        get_conn().rollback()
    except Exception:  # noqa: BLE001
        pass


def now():
    """Return the current timestamp without microseconds."""

    return datetime.datetime.now().replace(
        microsecond=0
    )


def as_datetime(value):
    """Convert SQLite string timestamps to datetime objects.

    MySQL already returns datetime objects.
    """

    if value is None:
        return None

    if isinstance(value, datetime.datetime):
        return value

    text = str(value)

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
    )

    for fmt in formats:
        try:
            return datetime.datetime.strptime(
                text,
                fmt,
            )
        except ValueError:
            continue

    return None


def healthcheck():
    """Check whether the configured database is reachable."""

    try:
        query_one("SELECT 1 AS ok")

        return True, "connected"

    except DatabaseUnavailable as exc:
        return False, str(exc)

    except Exception as exc:  # noqa: BLE001
        return False, str(exc)