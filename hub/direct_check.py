import os
import sqlite3
from pathlib import Path

def get_db_path():
    db_path = os.environ.get("RESKIOSK_DB_PATH")
    if not db_path:
        if os.name == 'nt':
            base = Path(os.environ.get('APPDATA')) / "ResKiosk"
        else:
            base = Path.home() / ".local" / "share" / "reskiosk"
        db_path = str(base / "reskiosk.db")
    return db_path

def check_db():
    path = get_db_path()
    print(f"Checking database at: {path}")
    if not os.path.exists(path):
        print("Database file does not exist.")
        return

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM kb_articles")
        count = cursor.fetchone()[0]
        print(f"Total articles: {count}")
        
        cursor.execute("SELECT id, question FROM kb_articles ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]} | Question: {row[1]}")
            
        cursor.execute("SELECT kb_version FROM kb_meta LIMIT 1")
        version = cursor.fetchone()
        if version:
            print(f"KB Version: {version[0]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
