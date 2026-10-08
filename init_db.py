"""Zero-setup database bootstrap.

MySQL is the deployment target, and database/schema.sql + database/seed.sql
are written for it. This script lets the same two files build a local SQLite
database instead, so CivicPulse can be demoed on a laptop with no MySQL server
running.

Usage:
    python init_db.py
    python init_db.py --driver mysql

Set DB_DRIVER=sqlite in .env to use the SQLite file.
"""

import argparse
import os
import re
import sqlite3
import sys

from config import Config


HERE = os.path.dirname(os.path.abspath(__file__))

SCHEMA = os.path.join(HERE, "database", "schema.sql")
SEED = os.path.join(HERE, "database", "seed.sql")


# ----------------------------------------------------------------------
# MySQL -> SQLite translation
# ----------------------------------------------------------------------

UNIT = {
    "HOUR": "hours",
    "DAY": "days",
    "MINUTE": "minutes",
    "MONTH": "months",
}


def to_sqlite(sql):
    """Convert MySQL schema/seed SQL into SQLite-compatible SQL."""

    # Remove MySQL database-selection statements.
    sql = re.sub(
        r"^\s*(?:CREATE DATABASE|USE|SET FOREIGN_KEY_CHECKS)\b[^;]*;",
        "",
        sql,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    sql = re.sub(
        r"TRUNCATE TABLE (\w+);",
        r"DELETE FROM \1;",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"\bINT\s+AUTO_INCREMENT\s+PRIMARY KEY\b",
        "INTEGER PRIMARY KEY AUTOINCREMENT",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"\s+ENGINE\s*=\s*\w+",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"\s+DEFAULT\s+CHARACTER SET[^;,\n]*",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"\s+ON UPDATE CURRENT_TIMESTAMP",
        "",
        sql,
        flags=re.IGNORECASE,
    )

    def interval(match):
        amount = match.group(1)
        unit = match.group(2).upper()

        return "datetime('now', 'localtime', '-%s %s')" % (
            amount,
            UNIT.get(unit, "hours"),
        )

    sql = re.sub(
        r"DATE_SUB\s*\(\s*NOW\s*\(\s*\)\s*,\s*INTERVAL\s+(\d+)\s+(\w+)\s*\)",
        interval,
        sql,
        flags=re.IGNORECASE,
    )

    sql = re.sub(
        r"\bNOW\s*\(\s*\)",
        "datetime('now', 'localtime')",
        sql,
        flags=re.IGNORECASE,
    )

    return sql


# ----------------------------------------------------------------------
# SQLite
# ----------------------------------------------------------------------


def build_sqlite(path):
    """Build a fresh SQLite database from schema.sql and seed.sql."""

    if os.path.exists(path):
        os.remove(path)

    os.makedirs(os.path.dirname(path), exist_ok=True)

    conn = sqlite3.connect(path)

    conn.execute("PRAGMA foreign_keys = OFF")

    for source in (SCHEMA, SEED):
        with open(source, encoding="utf-8") as handle:
            sql = handle.read()

        conn.executescript(to_sqlite(sql))

    conn.commit()

    counts = {}

    tables = (
        "users",
        "departments",
        "categories",
        "issues",
        "issue_reports",
        "issue_support",
        "ai_analysis",
        "issue_status_history",
        "notifications",
    )

    for table in tables:
        counts[table] = conn.execute(
            "SELECT COUNT(*) FROM %s" % table
        ).fetchone()[0]

    conn.close()

    return counts


# ----------------------------------------------------------------------
# MySQL / Aiven
# ----------------------------------------------------------------------


def build_mysql():
    """Build and seed the configured MySQL database."""

    try:
        import mysql.connector
    except ImportError:
        print(
            "mysql-connector-python is not installed. "
            "Run: pip install -r requirements.txt"
        )
        return 1

    print("Connecting to MySQL...")
    print("Host:", Config.DB_HOST)
    print("Port:", Config.DB_PORT)
    print("Database:", Config.DB_NAME)

    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,

            # Aiven requires an SSL connection.
            # Certificate verification is disabled because
            # the project does not currently provide a CA certificate.
            ssl_verify_cert=False,

            autocommit=True,
        )

    except Exception as exc:
        print("MySQL connection failed:")
        print(exc)
        return 1

    cursor = conn.cursor()

    try:
        # --------------------------------------------------------------
        # Run schema.sql
        # --------------------------------------------------------------

        print("Running schema.sql...")

        with open(SCHEMA, encoding="utf-8") as handle:
            schema_sql = handle.read()

        # Aiven already provides the configured database.
        # Remove CREATE DATABASE and USE statements.
        schema_sql = re.sub(
            r"CREATE\s+DATABASE\s+IF\s+NOT\s+EXISTS\s+\w+\s*;",
            "",
            schema_sql,
            flags=re.IGNORECASE,
        )

        schema_sql = re.sub(
            r"USE\s+\w+\s*;",
            "",
            schema_sql,
            flags=re.IGNORECASE,
        )

        # Execute SQL statements individually.
        for statement in schema_sql.split(";"):
            statement = statement.strip()

            if statement:
                cursor.execute(statement)

        print("Schema created successfully.")

        # --------------------------------------------------------------
        # Run seed.sql
        # --------------------------------------------------------------

        print("Running seed.sql...")

        with open(SEED, encoding="utf-8") as handle:
            seed_sql = handle.read()

        # Remove USE statements if present.
        seed_sql = re.sub(
            r"USE\s+\w+\s*;",
            "",
            seed_sql,
            flags=re.IGNORECASE,
        )

        for statement in seed_sql.split(";"):
            statement = statement.strip()

            if statement:
                cursor.execute(statement)

        print("Seed data inserted successfully.")

    except Exception as exc:
        print("Database initialization failed:")
        print(exc)
        return 1

    finally:
        cursor.close()
        conn.close()

    print(
        "MySQL database '%s' created and seeded."
        % Config.DB_NAME
    )

    return 0


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Create and seed the CivicPulse database."
    )

    parser.add_argument(
        "--driver",
        choices=["sqlite", "mysql"],
        default="sqlite",
    )

    args = parser.parse_args()

    if args.driver == "mysql":
        return build_mysql()

    counts = build_sqlite(Config.SQLITE_PATH)

    print(
        "SQLite database built at %s"
        % Config.SQLITE_PATH
    )

    for table, count in counts.items():
        print(
            "  %-22s %4d rows"
            % (table, count)
        )

    print(
        "\nSet DB_DRIVER=sqlite in your .env, "
        "then run: python app.py"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())