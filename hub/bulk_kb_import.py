import json
import argparse
import os
import sys
from datetime import datetime

# Add the project root to sys.path to allow importing hub modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hub.db.session import SessionLocal
from hub.db import schema
from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text

def bulk_import(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            articles_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON format: {e}")
            return

    if not isinstance(articles_data, list):
        print("Error: JSON must be a list of articles.")
        return

    db = SessionLocal()
    embedder = None
    try:
        embedder = load_embedder()
    except Exception as e:
        print(f"Warning: Could not load embedder. Articles will be imported without embeddings. Error: {e}")

    imported_count = 0
    error_count = 0

    print(f"Starting bulk import of {len(articles_data)} items...")

    for data in articles_data:
        try:
            if "question" not in data or "answer" not in data:
                print(f"Skipping article missing question or answer: {data.get('question', 'Unknown')}")
                error_count += 1
                continue

            import time as _time
            now = int(_time.time())
            tags_raw = data.get("tags", [])
            tags_str = ",".join(tags_raw) if isinstance(tags_raw, list) else (tags_raw or "")

            article = schema.KBArticle(
                question=data["question"],
                answer=data["answer"],
                category=data.get("category", "General"),
                tags=tags_str,
                enabled=1 if data.get("enabled", True) else 0,
                source=data.get("source", "import"),
                created_at=now,
                last_updated=now,
            )

            if embedder:
                try:
                    text = get_embeddable_text(article)
                    vec = embedder.embed_text(text)
                    article.embedding = serialize_embedding(vec)
                except Exception as e:
                    print(f"Warning: Failed to embed article '{article.question}': {e}")

            db.add(article)
            imported_count += 1
            if imported_count % 5 == 0:
                print(f"Processed {imported_count} articles...")

        except Exception as e:
            print(f"Error importing article '{data.get('question', 'Unknown')}': {e}")
            error_count += 1

    # Bump SystemVersion
    try:
        import time as _time
        sv = db.query(schema.SystemVersion).first()
        if not sv:
            sv = schema.SystemVersion(kb_version=1, last_published=int(_time.time()))
            db.add(sv)
        else:
            sv.kb_version = (sv.kb_version or 0) + 1
            sv.last_published = int(_time.time())
        db.add(sv)
    except Exception as e:
        print(f"Warning: Could not update SystemVersion: {e}")

    db.commit()
    db.close()

    print("\nImport Complete!")
    print(f"Successfully imported: {imported_count}")
    print(f"Failed: {error_count}")
    print(f"KB Version incremented.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk import articles into ResKiosk Knowledge Base")
    parser.get_default("file")
    parser.add_argument("--file", type=str, required=True, help="Path to the JSON file containing articles")
    
    args = parser.parse_args()
    bulk_import(args.file)
