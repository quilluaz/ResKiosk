import requests
import time
import os

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("RESKIOSK_LLM_MODEL", "gemma3:4b")
TIMEOUT_SECONDS = 30  # First inference can be slow due to cold model load

SYSTEM_PROMPT = """You are a helpful information assistant for an evacuation/shelter center.
Your role is to answer questions from evacuees clearly and concisely.

Rules:
- Keep the response to 2-4 sentences maximum.
- Use simple, calm language appropriate for stressed evacuees.
- If you don't know the answer, say so honestly and suggest asking a volunteer.
- Respond in plain conversational English only - no bullet points, no lists, no markdown."""


def direct_answer(query: str) -> str:
    """
    Send user query directly to LLM for a conversational response.
    Falls back to a safe message on error/timeout.
    """
    if not query:
        return "I didn't catch that. Could you try again?"

    start_time = time.time()

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 200,
            "top_p": 0.9
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get("message", {}).get("content", "").strip()

        if not answer:
            return "I'm sorry, I couldn't process that right now. Please try again."

        elapsed = time.time() - start_time
        print(f"[Formatter] LLM direct answer in {elapsed:.2f}s")
        return answer

    except requests.exceptions.Timeout:
        print(f"[Formatter] LLM timeout after {TIMEOUT_SECONDS}s")
        return "I'm taking too long to respond. Please try again or ask a volunteer."
    except Exception as e:
        print(f"[Formatter] Ollama error ({e})")
        return "I'm sorry, I'm having trouble right now. Please ask a volunteer for help."


FORMAT_SYSTEM_PROMPT = """You are Reze, the response formatter for an evacuation center information system.
You will be given a verified knowledge base entry as JSON containing 'question' and 'answer' fields.
Your only job is to rewrite the 'answer' into a short, clear, spoken response. The 'question' field is for context only.

Rules:
- Do NOT add any information not present in the 'answer' field.
- Do NOT speculate, infer, or expand beyond what is written.
- Use calm, reassuring language appropriate for stressed evacuees.
- Respond in plain conversational English only - no bullet points, no lists, no markdown.
- Keep the response to 2-3 sentences maximum.
- If include_intro is true, start with a short intro like "I'm Reze." and then give the answer.
- If the text is already short and clear, return it with minimal changes."""


def _postprocess_formatted(text: str, fallback: str) -> str:
    """Enforce plain text rules: no bullets/markdown, 2-3 sentences max."""
    if not text or not text.strip():
        return fallback

    cleaned = text.replace("*", " ").replace("-", " ").replace("•", " ")
    cleaned = cleaned.replace("`", "").replace("#", "").replace("_", " ")
    cleaned = " ".join(cleaned.split())

    import re
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return fallback
    trimmed = " ".join(sentences[:3])
    return trimmed.strip() if trimmed.strip() else fallback


def format_response(kb_article_json: str, query: str = "", history_str: str = "", include_intro: bool = False) -> str:
    """
    Formats a verified KB article (JSON string) into a spoken response using LLM.
    The LLM is strictly constrained to only reformat - never generate new content.
    Falls back to raw article body on error/timeout.
    """
    if not kb_article_json:
        return ""

    # Try to extract raw answer as fallback
    fallback_text = kb_article_json
    try:
        import json
        parsed = json.loads(kb_article_json)
        # Use 'answer' field from the KB article JSON
        fallback_text = parsed.get("answer", kb_article_json)
    except Exception:
        pass

    # Build the prompt dynamically to include history if present
    prompt_content = f"KB Entry:\n{kb_article_json}\n\n"
    if history_str:
        prompt_content += f"Previous Conversation Context:\n{history_str}\n\n"
    prompt_content += f"User's Question: {query}\n\ninclude_intro: {str(include_intro).lower()}\n\nFormatted spoken response:"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": FORMAT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content}
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 150,
            "top_p": 0.9
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        result = response.json()
        formatted = result.get("message", {}).get("content", "").strip()
        if not formatted:
            print("[Formatter] Empty LLM response, using raw KB text.")
        return _postprocess_formatted(formatted, fallback_text)
    except Exception as e:
        print(f"[Formatter] Ollama unavailable ({e}), using raw KB text.")
        return fallback_text


def check_ollama_available() -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        available = any(MODEL_NAME.split(":")[0] in m for m in models)
        if not available:
            print(f"[Formatter] WARNING: Model '{MODEL_NAME}' not found in Ollama. Run: ollama pull {MODEL_NAME}")
        return available
    except Exception:
        print(f"[Formatter] WARNING: Ollama not reachable at {OLLAMA_URL}")
        return False
