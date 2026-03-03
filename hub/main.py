from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hub.api import routes_system, routes_kb, routes_admin, routes_query, routes_network, routes_emergency, routes_messages, routes_lora, routes_auth
from hub.db.init_db import init_db

app = FastAPI(title="ResKiosk Hub", version="0.2")

# CORS (allow all for hub LAN context)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    from hub.core.logger_stream import setup_log_capture
    setup_log_capture()
    init_db()
    _embed_missing_articles()
    _prewarm_models()
    _lora_auto_connect()
    # Cloud connectivity manager disabled (offline-first rollback).


def _embed_missing_articles():
    """On startup, generate embeddings for any articles that don't have them."""
    from hub.db.session import SessionLocal
    from hub.db import schema as s
    from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text

    db = SessionLocal()
    try:
        missing = db.query(s.KBArticle).filter(
            s.KBArticle.enabled == 1,
            (s.KBArticle.embedding == None) | (s.KBArticle.embedding == b"")
        ).all()

        if not missing:
            print("[Startup] All articles have embeddings.")
            return

        print(f"[Startup] {len(missing)} articles missing embeddings, generating...")
        embedder = load_embedder()
        count = 0
        for art in missing:
            try:
                text = get_embeddable_text(art)
                vec = embedder.embed_text(text)
                art.embedding = serialize_embedding(vec)
                count += 1
            except Exception as e:
                print(f"[Startup] Failed to embed article {art.id}: {e}")

        db.commit()
        print(f"[Startup] Embedded {count}/{len(missing)} articles.")
    except Exception as e:
        print(f"[Startup] Embedding check failed: {e}")
    finally:
        db.close()


def _prewarm_models():
    """Pre-load embedding model, init intent classifier, and warm Ollama in background."""
    import time
    import threading

    t0 = time.time()
    try:
        from hub.retrieval.embedder import load_embedder
        from hub.retrieval.intent import IntentClassifier
        from hub.retrieval import search as search_module
        embedder = load_embedder()
        embedder.embed_text("warmup")
        print(f"[Startup] Embedding model warm in {time.time()-t0:.1f}s")
        intent_classifier = IntentClassifier(embedder)
        search_module.set_intent_classifier(intent_classifier)
        print("[Startup] Intent classifier ready.")
    except Exception as e:
        print(f"[Startup] Embedding warmup failed: {e}")

    # Warm NLLB translator so translation failures surface at startup instead of
    # on the first non-English query, and to reduce latency for that first call.
    try:
        from hub.retrieval import translator
        model, tokenizer = translator._load_model()
        if model is not None:
            print("[Startup] NLLB translator ready.")
        else:
            print("[Startup] WARNING: NLLB translator not available — translation disabled.")
    except Exception as e:
        print(f"[Startup] NLLB warmup failed (non-fatal): {e}")

    def _warm_ollama():
        try:
            from hub.retrieval.formatter import check_ollama_available, OLLAMA_URL, MODEL_NAME
            import requests as _req
            if check_ollama_available():
                t1 = time.time()
                _req.post(f"{OLLAMA_URL}/api/chat", json={
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "options": {"num_predict": 1}
                }, timeout=60)
                print(f"[Startup] Ollama model warm in {time.time()-t1:.1f}s")
            else:
                print("[Startup] WARNING: Ollama not available — LLM features will be degraded.")
        except Exception as e:
            print(f"[Startup] Ollama warmup failed (non-fatal): {e}")

    threading.Thread(target=_warm_ollama, daemon=True).start()


def _lora_auto_connect():
    """Attempt to reconnect to a previously-used ESP+LoRa device."""
    try:
        from hub.api.routes_lora import startup_auto_connect
        startup_auto_connect()
    except Exception as e:
        print(f"[Startup] LoRa auto-connect skipped: {e}")


from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
import os
import sys
from pathlib import Path


def get_base_path():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS if hasattr(sys, "_MEIPASS") else sys.executable).parent
    return Path(__file__).parent.parent


app.include_router(routes_auth.router)
app.include_router(routes_system.router)
app.include_router(routes_network.router)
app.include_router(routes_kb.router)
app.include_router(routes_admin.router)
app.include_router(routes_query.router)
app.include_router(routes_emergency.router)
app.include_router(routes_messages.router)
app.include_router(routes_lora.router)
# Cloud routes disabled (offline-first rollback).

# Serve console static files
base = get_base_path()
static_dir = None
for candidate in (
    base / "console_static",       # PyInstaller bundle location
    base / "console" / "dist",     # Source repo location (cwd-independent)
):
    if candidate.exists():
        static_dir = candidate
        break

if static_dir is not None:
    app.mount("/console", StaticFiles(directory=str(static_dir), html=True), name="console")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/")
async def root():
    if static_dir is not None:
        return RedirectResponse(url="/console/")
    return {"status": "ok", "message": "Hub API is running. Console assets were not found."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
