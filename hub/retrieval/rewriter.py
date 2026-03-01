"""
Optional query rewriter for noisy STT. Feature-flagged, off by default.
Only rewrites when intent is unclear, retrieval score < 0.40, and word count 4-30.
"""
import os
import time
import requests

REWRITE_ENABLED = os.environ.get("RESKIOSK_QUERY_REWRITE", "false").lower() == "true"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("RESKIOSK_LLM_MODEL", "llama3.2:3b")
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

CONTEXT_SYSTEM_PROMPT = """You are a conversational query resolver for an evacuation center.
Your job is to take a user's follow-up question and the recent conversation history, and rewrite it into a single standalone question that contains all necessary context.

Rules:
1. If the question is already standalone (e.g. "Where is the medical station?"), return it unchanged.
2. If the question is a follow-up (e.g. "When?", "Where?", "Can you tell me more?"), resolve pronouns and missing context using the history.
3. Output the standalone question ONLY. No explanations.
4. Keep it short and natural."""

def rewrite_contextual(query: str, history: list) -> str:
    """
    Rewrites a short follow-up query into a standalone query using session history.
    """
    if not query or not history:
        return query
    
    lowered = query.lower()
    # List of common topics that should usually be standalone
    standalone_topics = ["medical", "food", "sleeping", "registration", "wash", "toilet", "water", "shower"]
    if any(topic in lowered for topic in standalone_topics) and len(query.split()) >= 2:
        print(f"[Rewriter] Standalone topic detected: '{query}'. Skipping rewrite.")
        return query

    # Only rewrite if the query is very short or likely a follow-up (e.g. "When?", "Where is it?")
    # Generally, if it has more than 5 words and contains a topic, it's likely standalone
    if len(query.split()) > 5:
        # Check for pronouns or connecting words that imply follow-up
        cues = ["it", "they", "there", "that", "them", "then", "when", "how about", "what about", "and", "where"]
        if not any(cue in lowered.split() for cue in cues):
            print(f"[Rewriter] Query looks standalone: '{query}'. Skipping rewrite.")
            return query

    # Format history for the prompt (limit to last 2 turns)
    context_str = ""
    for turn in history[-2:]:
        context_str += f"User: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}\n"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": CONTEXT_SYSTEM_PROMPT},
            {"role": "user", "content": f"History:\n{context_str}\n\nFollow-up: {query}\n\nStandalone Question:"}
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 50},
    }

    try:
        print(f"[Rewriter] Resolving follow-up: '{query}' with {len(history)} turns of history.")
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=10 # Contextual rewrite should be fast
        )
        response.raise_for_status()
        result = response.json()
        rewritten = result.get("message", {}).get("content", "").strip()
        
        # Strip quotes if the LLM added them
        rewritten = rewritten.strip('"').strip("'")
        
        if rewritten and len(rewritten.split()) < 20:
            print(f"[Rewriter] RESOLVED: '{query}' -> '{rewritten}'")
            return rewritten
        print(f"[Rewriter] Result too long or empty, ignoring: '{rewritten}'")
        return query
    except Exception as e:
        print(f"[Rewriter] Contextual resolve FAILED: {e}")
        return query
