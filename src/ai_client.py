import logging

import httpx

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_PROVIDER,
    LLM_TIMEOUT,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Ошибка при обращении к LLM (Ollama, Gemini и др.)."""


class LLMQuotaError(LLMError):
    """Исчерпана квота API (429)."""


class LLMAuthError(LLMError):
    """Неверный или неподходящий API-ключ."""


async def chat_completion(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> str:
    provider = LLM_PROVIDER.lower()
    if provider == "gemini":
        return await _gemini_chat(system_prompt, messages)
    if provider == "ollama":
        return await _ollama_chat(system_prompt, messages)
    raise LLMError(
        f"Неизвестный LLM_PROVIDER: {LLM_PROVIDER!r}. "
        "Допустимо: ollama, gemini"
    )


async def _ollama_chat(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> str:
    """Ollama Chat API: POST /api/chat"""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512},
    }
    url = f"{OLLAMA_BASE_URL}/api/chat"

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError as exc:
        raise LLMError(
            f"Не удалось подключиться к Ollama ({OLLAMA_BASE_URL}). "
            f"Запустите Ollama и выполните: ollama pull {OLLAMA_MODEL}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"Ollama: HTTP {exc.response.status_code}") from exc
    except httpx.TimeoutException as exc:
        raise LLMError("Превышено время ожидания ответа от Ollama.") from exc

    content = (data.get("message") or {}).get("content", "").strip()
    if not content:
        raise LLMError("Пустой ответ от Ollama.")
    return content


async def _gemini_chat(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> str:
    """
    Google Gemini API (REST):
    https://ai.google.dev/gemini-api/docs/text-generation
    """
    contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 512,
        },
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(
                url,
                params={"key": GEMINI_API_KEY},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        detail_lower = detail.lower()
        if status == 429 or "quota" in detail_lower or "rate limit" in detail_lower:
            raise LLMQuotaError(detail or "quota exceeded") from exc
        if status in (401, 403) or "api key" in detail_lower or "permission" in detail_lower:
            raise LLMAuthError(detail or "invalid API key") from exc
        logger.error("Gemini HTTP %s: %s", status, detail[:500])
        raise LLMError(f"Gemini: HTTP {status}") from exc
    except httpx.TimeoutException as exc:
        raise LLMError("Превышено время ожидания ответа от Gemini.") from exc

    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMError("Gemini вернула пустой ответ (нет candidates).")

    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise LLMError("Пустой текст в ответе Gemini.")
    return text


# Обратная совместимость
OllamaError = LLMError
