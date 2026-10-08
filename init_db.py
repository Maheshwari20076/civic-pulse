"""Zero-setup database bootstrap.

MySQL is the deployment target, and `database/schema.sql` + `database/seed.sql`
are written for it. This script lets the same two files build a local SQLite
database instead, so CivicPulse can be demoed on a laptop with no MySQL server
running - useful when the projector is on and XAMPP is not.

    python init_db.py                 # builds the SQLite demo database
    python init_db.py --driver mysql  # runs schema + seed against MySQL

Set DB_DRIVER=sqlite in .env to make the app use the SQLite file.
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
# MySQL -> SQLite translation. Deliberately small: the SQL files are written
# in a constrained style precisely so this stays a handful of rules.
# ----------------------------------------------------------------------
UNIT = {"HOUR": "hours", "DAY": "days", "MINUTE": "minutes", "MONTH": "months"}


def to_sqlite(sql):
    # \b matters: without it "USE" also matches the start of a "user_id" column
    # and the lazy [\s\S]*? then eats the rest of the CREATE TABLE body.
    sql = re.sub(r"^[ \t]*(?:CREATE DATABASE|USE|SET FOREIGN_KEY_CHECKS)\b[^;]*;", "",
                 sql, flags=re.MULTILINE | re.IGNORECASE)
    sql = re.sub(r"TRUNCATE TABLE (\w+);", r"DELETE FROM \1;", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bINT\s+AUTO_INCREMENT\s+PRIMARY KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT",
                 sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+ENGINE\s*=\s*\w+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+DEFAULT\s+CHARACTER SET[^;,\n]*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s+ON UPDATE CURRENT_TIMESTAMP", "", sql, flags=re.IGNORECASE)

    def interval(match):
        amount, unit = match.group(1), match.group(2).upper()
        return "datetime('now', 'localtime', '-%s %s')" % (amount, UNIT.get(unit, "hours"))

    sql = re.sub(r"DATE_SUB\(\s*NOW\(\)\s*,\s*INTERVAL\s+(\d+)\s+(\w+)\s*\)", interval,
                 sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bNOW\(\)", "datetime('now', 'localtime')", sql, flags=re.IGNORECASE)
    return sql


def build_sqlite(path):
    if os.path.exists(path):
        os.remove(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = OFF")
    for source in (SCHEMA, SEED):
        with open(source, encoding="utf-8") as handle:
            conn.executescript(to_sqlite(handle.read()))
    conn.commit()
    counts = {}
    for table in ("users", "departments", "categories", "issues", "issue_reports",
                  "issue_support", "ai_analysis", "issue_status_history", "notifications"):
        counts[table] = conn.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
    conn.close()
    return counts


def build_mysql():
    try:
        import mysql.connector
    except ImportError:
        print("mysql-connector-python is not installed. Run: pip install -r requirements.txt")
        return 1
    conn = mysql.connector.connect(
        host=Config.DB_HOST, port=Config.DB_PORT,
        user=Config.DB_USER, password=Config.DB_PASSWORD, autocommit=True,
    )
    cursor = conn.cursor()
    for source in (SCHEMA, SEED):
        with open(source, encoding="utf-8") as handle:
            for _ in cursor.execute(handle.read(), multi=True):
                pass
    cursor.close()
    conn.close()
    print("MySQL database '%s' created and seeded." % Config.DB_NAME)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Create and seed the CivicPulse database.")
    parser.add_argument("--driver", choices=["sqlite", "mysql"], default="sqlite")
    args = parser.parse_args()

    if args.driver == "mysql":
        return build_mysql()

    counts = build_sqlite(Config.SQLITE_PATH)
    print("SQLite database built at %s" % Config.SQLITE_PATH)
    for table, count in counts.items():
        print("  %-22s %4d rows" % (table, count))
    print("\nSet DB_DRIVER=sqlite in your .env, then run: python app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
