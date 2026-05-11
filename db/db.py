import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent

DB_FILE = BASE_DIR / "ContactBook.db"

SCHEMA_FILE = BASE_DIR / "schema.sql"

def get_db_connection():
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_database(conn):
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f" Файл схемы не найден: {SCHEMA_FILE}")
    
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())