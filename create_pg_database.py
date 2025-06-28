#!/usr/bin/env python
# File: create_pg_database.py
# Author: Oluwatobiloba Light
"""Creates a Postgres Database for AutoResume"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

PG_SUPERUSER = "postgres"
PG_SUPERPASS = "postgres"
PG_HOST = "localhost"
PG_PORT = 5432

NEW_DB = "autoresume_db"
NEW_USER = "autoresum_admin"
NEW_PASS = "admin123."

def create_db_and_user():
    conn = psycopg2.connect(
        dbname="postgres",
        user=PG_SUPERUSER,
        password=PG_SUPERPASS,
        host=PG_HOST,
        port=PG_PORT
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{NEW_DB}';")
    if not cur.fetchone():
        cur.execute(f"CREATE DATABASE {NEW_DB};")

    cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{NEW_USER}';")
    if not cur.fetchone():
        cur.execute(f"CREATE USER {NEW_USER} WITH PASSWORD '{NEW_PASS}';")
        cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {NEW_DB} TO {NEW_USER};")

    cur.close()
    conn.close()

if __name__ == "__main__":
    create_db_and_user()
