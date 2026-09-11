import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# Single swap point for the OpenRouter model id (AGENTS.md: config in one place).
LLM_MODEL = "google/gemma-4-26b-a4b-it:free"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_SYSTEM_PROMPT = "You are StyleScout, a helpful fashion assistant."
RATE_LIMIT_RETRY_SECONDS = 3.5

logger = logging.getLogger(__name__)


class LLMRateLimitError(Exception):
    """Raised when OpenRouter returns HTTP 429 after one retry."""


def ask_llm(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 300,
) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "OPENROUTER_API_KEY bulunamadı."

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt or DEFAULT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = _post_chat(headers, payload)
        if response.status_code == 429:
            logger.info(
                "OpenRouter HTTP 429; retrying once after %.1fs",
                RATE_LIMIT_RETRY_SECONDS,
            )
            time.sleep(RATE_LIMIT_RETRY_SECONDS)
            response = _post_chat(headers, payload)
            if response.status_code == 429:
                raise LLMRateLimitError("OpenRouter rate limited (HTTP 429)")

        if response.status_code != 200:
            return f"API Error: {response.status_code}"

        return response.json()["choices"][0]["message"]["content"]

    except LLMRateLimitError:
        raise
    except requests.exceptions.Timeout:
        return "API Zaman Aşımı Hatası."
    except requests.exceptions.RequestException:
        return "API Bağlantı Hatası."


def _post_chat(headers: dict, payload: dict):
    return requests.post(
        OPENROUTER_CHAT_URL,
        headers=headers,
        json=payload,
        timeout=10,
    )
