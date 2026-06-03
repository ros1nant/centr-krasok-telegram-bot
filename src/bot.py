import logging

from telegram import Update, User
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from src.ai_client import LLMAuthError, LLMError, LLMQuotaError, chat_completion
from src.config import (
    LLM_PROVIDER,
    MAX_CONTEXT_MESSAGES,
    MAX_REPLY_LENGTH,
    TELEGRAM_BOT_TOKEN,
    validate_llm_config,
    validate_telegram_token,
)
from src.context_manager import DialogContext
from src.guardrails import (
    OFF_TOPIC_REPLY,
    FALLBACK_NO_INFO,
    is_likely_off_topic,
    sanitize_reply,
)
from src.knowledge import build_system_prompt, load_knowledge

logger = logging.getLogger(__name__)

EXAMPLE_QUESTIONS = [
    "Чем занимается компания?",
    "Какие услуги предоставляет?",
    "Где находится офис?",
    "Какие бренды есть в каталоге?",
    "Кто клиенты компании?",
    "Есть ли вакансии?",
    "Как связаться с менеджером?",
]

GREETING_TRIGGERS = {
    "/start",
    "start",
    "привет",
    "здравствуйте",
    "здравствуй",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "hello",
    "hi",
    "hey",
}

THINKING = "Секунду, подбираю ответ..."

context_store = DialogContext(max_pairs=MAX_CONTEXT_MESSAGES)
_system_prompt: str | None = None


def get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = build_system_prompt(load_knowledge())
    return _system_prompt


def _display_name(user: User | None) -> str:
    if not user:
        return "друг"
    if user.username:
        return f"@{user.username}"
    if user.first_name:
        return user.first_name
    return "друг"


def build_welcome_message(user: User | None) -> str:
    name = _display_name(user)
    examples = "\n".join(f"• {q}" for q in EXAMPLE_QUESTIONS)
    return (
        f"Здравствуйте, {name}!\n\n"
        "Я AI-ассистент «Центр Красок #1» — помогу с вопросами о нашей компании.\n\n"
        "Просто напишите сообщение, как в обычном чате. Вот примеры вопросов:\n\n"
        f"{examples}\n\n"
        "Скопируйте любой вопрос или задайте свой."
    )


def _is_greeting(text: str) -> bool:
    normalized = text.lower().strip()
    if normalized in GREETING_TRIGGERS:
        return True
    return normalized.startswith("/start")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user_text = (update.message.text or "").strip()

    if not user_text:
        return

    if _is_greeting(user_text):
        await update.message.reply_text(
            build_welcome_message(update.effective_user)
        )
        return

    if is_likely_off_topic(user_text):
        await update.message.reply_text(OFF_TOPIC_REPLY)
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    status_msg = await update.message.reply_text(THINKING)

    context_store.add_user(chat_id, user_text)
    history = context_store.get_messages(chat_id)

    try:
        reply = await chat_completion(get_system_prompt(), history)
        reply = sanitize_reply(reply, MAX_REPLY_LENGTH)
        if not reply:
            reply = FALLBACK_NO_INFO
    except LLMQuotaError:
        logger.warning("Gemini quota exceeded")
        reply = (
            "Сейчас исчерпан бесплатный лимит запросов к AI (Google Gemini).\n\n"
            "Что можно сделать:\n"
            "• подождать до завтра (лимит обновляется раз в сутки);\n"
            "• в .env сменить модель, например: GEMINI_MODEL=gemini-2.5-flash-lite;\n"
            "• или перейти на Ollama локально: LLM_PROVIDER=ollama.\n\n"
            "По срочным вопросам — менеджеры: +7 (777) 292-84-01, https://centr-krasok.kz/"
        )
        context_store.clear(chat_id)
    except LLMAuthError:
        logger.error("Gemini auth error — проверьте API-ключ")
        reply = (
            "Не удалось подключиться к AI: проверьте ключ Gemini в .env.\n\n"
            "Нужен ключ из Google AI Studio (начинается с AIzaSy...):\n"
            "https://aistudio.google.com/apikey\n\n"
            "Контакты: +7 (777) 292-84-01, https://centr-krasok.kz/"
        )
        context_store.clear(chat_id)
    except LLMError as exc:
        logger.exception("LLM error (%s)", LLM_PROVIDER)
        reply = (
            "Сейчас не могу сформировать ответ. Попробуйте через минуту.\n\n"
            f"Контакты: +7 (777) 292-84-01, https://centr-krasok.kz/"
        )
        logger.debug("LLM detail: %s", exc)
        context_store.clear(chat_id)
    except Exception:
        logger.exception("Unexpected error")
        reply = FALLBACK_NO_INFO
        context_store.clear(chat_id)

    context_store.add_assistant(chat_id, reply)

    try:
        await status_msg.edit_text(reply)
    except Exception:
        await update.message.reply_text(reply)


def build_application() -> Application:
    validate_telegram_token()
    validate_llm_config()
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # /start и другие команды тоже обрабатываем как текст через отдельный хендлер
    app.add_handler(MessageHandler(filters.COMMAND, handle_message))
    return app
