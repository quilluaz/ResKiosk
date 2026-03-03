import json
import os
from typing import Any

import requests

from hub.retrieval import formatter as local_formatter
from hub.retrieval.formatter_contract import FORMAT_SYSTEM_PROMPT, build_user_prompt
from hub.services.cloud_quota import reserve


class CloudFormatterError(Exception):
    pass


class CloudFormatter:
    def __init__(self) -> None:
        self.model = os.environ.get("RESKIOSK_CLOUD_FORMAT_MODEL", "gpt-4o-mini")
        self.timeout_secs = float(os.environ.get("RESKIOSK_CLOUD_FORMAT_TIMEOUT_SECS", "2.0"))
        self.api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        self.endpoint = os.environ.get("RESKIOSK_OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions")

    def _fallback_text(self, kb_article_json: str) -> str:
        try:
            parsed = json.loads(kb_article_json)
            return parsed.get("answer", kb_article_json)
        except Exception:
            return kb_article_json

    def format_response(
        self,
        kb_article_json: str,
        query: str = "",
        history_str: str = "",
        include_intro: bool = False,
    ) -> str:
        if not kb_article_json:
            return ""
        if not self.api_key:
            raise CloudFormatterError("OPENAI_API_KEY missing")

        allowed, reason = reserve("formatter")
        if not allowed:
            raise CloudFormatterError(reason or "formatter quota reached")

        prompt = build_user_prompt(kb_article_json, query, history_str, include_intro)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": FORMAT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 220,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout_secs,
            )
            response.raise_for_status()
            data = response.json()
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            fallback = self._fallback_text(kb_article_json)
            return local_formatter._postprocess_formatted(content, fallback)
        except Exception as exc:
            raise CloudFormatterError(str(exc)) from exc

