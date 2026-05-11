import sqlite3
from database import get_db_connection, init_database

def verify_database(conn):
    try:
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
              AND name IN ('departments', 'subdivisions', 'employees', 'users', 'favorites')
            ORDER BY name;
        """)
        tables = [row[0] for row in cursor.fetchall()]

        if len(tables) == 5:
            print("✅ База данных подключена и инициализирована успешно.")
            print(f"📋 Созданные таблицы: {', '.join(tables)}")
        else:
            print(f"⚠️ Создано таблиц: {len(tables)}. Ожидалось 5.")
            
    except sqlite3.Error as e:
        print(f"❌ Ошибка при проверке структуры: {e}")

if __name__ == "__main__":
    conn = get_db_connection()
    try:
        init_database(conn)
        verify_database(conn)
    finally:
        conn.close()