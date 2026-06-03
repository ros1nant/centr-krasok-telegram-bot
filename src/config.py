import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

_TOKEN_PLACEHOLDERS = {
    "",
    "ВСТАВЬТЕ_СЮДА_ТОКЕН_TELEGRAM_БОТА",
    "your_telegram_bot_token_here",
    "YOUR_BOT_TOKEN",
}
# Формат от @BotFather: 123456789:AAH... (цифры, двоеточие, буквы/цифры/_-)
_TOKEN_PATTERN = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")


def validate_telegram_token(token: str = TELEGRAM_BOT_TOKEN) -> None:
    if token in _TOKEN_PLACEHOLDERS or "ВСТАВЬТЕ" in token.upper():
        raise RuntimeError(
            "Не задан TELEGRAM_BOT_TOKEN.\n"
            "Локально: файл .env\n"
            "Render/Railway: вкладка Environment → Add Variable\n\n"
            "1. Telegram → @BotFather → /token\n"
            "2. Скопируйте токен: 123456789:AAH...\n"
            "3. TELEGRAM_BOT_TOKEN=ваш_токен"
        )
    if not _TOKEN_PATTERN.match(token):
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN в .env выглядит неверно.\n"
            "Токен должен быть как у @BotFather: числа, двоеточие, длинная строка.\n"
            "Пример: TELEGRAM_BOT_TOKEN=7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
        )

# ollama | gemini
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", os.getenv("OLLAMA_TIMEOUT", "120")))

# --- Ollama (локально) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# --- Google Gemini (облако, API-ключ) ---
# Ключ: https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

_GEMINI_PLACEHOLDERS = {"", "ВСТАВЬТЕ_GEMINI_API_KEY", "your_gemini_api_key_here"}

MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", "8"))
MAX_REPLY_LENGTH = int(os.getenv("MAX_REPLY_LENGTH", "4000"))

KNOWLEDGE_PATH = ROOT_DIR / "data" / "company_knowledge.md"


def validate_llm_config() -> None:
    if LLM_PROVIDER == "ollama":
        return
    if LLM_PROVIDER == "gemini":
        if GEMINI_API_KEY in _GEMINI_PLACEHOLDERS or "ВСТАВЬТЕ" in GEMINI_API_KEY.upper():
            raise RuntimeError(
                "Не задан GEMINI_API_KEY.\n"
                "Локально: .env | Render/Railway: Environment Variables\n"
                "Ключ: https://aistudio.google.com/apikey (формат AIzaSy...)\n"
                "LLM_PROVIDER=gemini"
            )
        if not GEMINI_API_KEY.startswith("AIza"):
            logger.warning(
                "GEMINI_API_KEY не начинается с AIza — возможно, это не ключ из AI Studio. "
                "Создайте ключ: https://aistudio.google.com/apikey"
            )
        return
    raise RuntimeError(
        f"LLM_PROVIDER={LLM_PROVIDER!r} не поддерживается. Используйте: ollama или gemini"
    )
