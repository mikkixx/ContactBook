import sqlite3
import os

DB_FILE = "ContactBook.db"
SCHEMA_FILE = "schema.sql"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_database(conn):
    if not os.path.exists(SCHEMA_FILE):
        raise FileNotFoundError(f"Файл схемы {SCHEMA_FILE} не найден в директории проекта")
    
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())