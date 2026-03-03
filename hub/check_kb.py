import os
import sys
from sqlalchemy.orm import Session

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hub.db.session import SessionLocal
from hub.db import schema

def check_kb():
    db = SessionLocal()
    articles = db.query(schema.KBArticle).all()
    print(f"Total articles in KB: {len(articles)}")
    for art in articles:
        print(f"ID: {art.id} | Question: {art.question} | Category: {art.category} | Enabled: {art.enabled}")

    sv = db.query(schema.SystemVersion).first()
    if sv:
        print(f"KB Version: {sv.kb_version} | Last Published: {sv.last_published}")
    else:
        print("SystemVersion not found.")

    db.close()

if __name__ == "__main__":
    check_kb()
