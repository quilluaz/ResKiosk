import os
import pickle
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Union

_embedder_instance = None

def get_models_path():
    """Return path to embedding model dir. Prefer env; else path relative to this package (reskiosk)."""
    path = os.environ.get("RESKIOSK_MODELS_PATH")
    if path:
        return path
    # Resolve relative to reskiosk root so it works regardless of CWD (e.g. python -m hub.main from anywhere)
    # embedder.py lives in reskiosk/hub/retrieval/ -> parent.parent.parent = reskiosk
    reskiosk_root = Path(__file__).resolve().parent.parent.parent
    return str(reskiosk_root / "packaging" / "hub_models")

class SecureEmbedder:
    def __init__(self):
        model_path = get_models_path()
        print(f"Loading embedding model from: {model_path}")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Embedding model path does not exist: {model_path}\n"
                "Run TO RUN\\02_download_models.bat (or: python packaging/bundle_models.py) to download the model."
            )
        self.model = SentenceTransformer(model_path, device='cpu', local_files_only=True)
    
    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        return self.model.encode(text, convert_to_numpy=True)

def load_embedder() -> SecureEmbedder:
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = SecureEmbedder()
    return _embedder_instance

def get_embeddable_text(article) -> str:
    """Canonical text used for embedding. Question + tags only.

    Answer/body is deliberately excluded — long answer text dominates
    the vector and reduces query-to-question similarity.
    """
    tags_str = ""
    try:
        raw_tags = getattr(article, "tags", "") or ""
        # tags is now a plain comma-separated string (e.g. "food,schedule")
        tags_str = " ".join(t.strip() for t in raw_tags.split(",") if t.strip())
    except Exception:
        pass
    question = getattr(article, "question", "") or ""
    return f"{question} {tags_str}".strip()


def serialize_embedding(vec: np.ndarray) -> bytes:
    return pickle.dumps(vec)

def deserialize_embedding(blob: bytes) -> np.ndarray:
    if not blob:
        return None
    return pickle.loads(blob)
