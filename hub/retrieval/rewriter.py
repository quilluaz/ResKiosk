"""
Optional query rewriter for noisy STT. Feature-flagged, off by default.
Only rewrites when intent is unclear, retrieval score < 0.40, and word count 4-30.
"""
import os
import time
import requests

REWRITE_ENABLED = os.environ.get("RESKIOSK_QUERY_REWRITE", "false").lower() == "true"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("RESKIOSK_REWRITE_MODEL") or os.environ.get("RESKIOSK_LLM_MODEL", "llama3.2:3b")
REWRITE_TIMEOUT = 15

REWRITE_SYSTEM_PROMPT = """You are a query cleaner for an evacuation center information system.
Your only job is to rewrite noisy speech-to-text output into a clean, short question.
Rules:
- Output one short sentence only
- Do not add information that was not in the input
- Do not answer the question
- Do not use bullet points or lists
- If the input is already clear, return it unchanged
- Maximum 12 words in output"""


def maybe_rewrite(query: str, intent: str, score: float) -> str:
    """
    If all guard conditions pass, call LLM to rewrite the query. Otherwise return query unchanged.
    """
    if not REWRITE_ENABLED:
        return query
    if intent != "unclear":
        return query
    if score >= 0.40:
        return query
    words = query.split()
    if len(words) < 4 or len(words) > 30:
        return query

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 30},
    }
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=REWRITE_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        rewritten = (result.get("message", {}).get("content", "") or "").strip()
        if not rewritten:
            return query
        if len(rewritten.split()) > 15:
            return query
        return rewritten
    except Exception:
        return query
