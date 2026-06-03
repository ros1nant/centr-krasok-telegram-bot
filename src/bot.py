import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from src.ai_client import LLMError, chat_completion
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

WELCOME = (
    "Здравствуйте! Я AI-ассистент «Центр Красок #1».\n\n"
    "Спросите о нашей компании: услуги, салоны в Алматы и Астане, "
    "бренды, доставка, программы для дизайнеров и строителей.\n\n"
    "Просто напишите вопрос — команды не нужны."
)

THINKING = "Секунду, подбираю ответ..."

context_store = DialogContext(max_pairs=MAX_CONTEXT_MESSAGES)
_system_prompt: str | None = None


def get_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = build_system_prompt(load_knowledge())
    return _system_prompt


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user_text = (update.message.text or "").strip()

    if not user_text:
        return

    # Первое сообщение /start — приветствие без вызова AI
    if user_text.lower() in {"/start", "start"}:
        await update.message.reply_text(WELCOME)
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
    except LLMError as exc:
        logger.exception("LLM error (%s)", LLM_PROVIDER)
        if LLM_PROVIDER == "gemini":
            hint = (
                "Проверьте GEMINI_API_KEY и GEMINI_MODEL в .env "
                "(ключ: https://aistudio.google.com/apikey)."
            )
        else:
            hint = (
                "Проверьте, что Ollama запущена, модель скачана "
                "(OLLAMA_BASE_URL, OLLAMA_MODEL)."
            )
        reply = (
            f"Сейчас не могу получить ответ от AI ({exc}).\n\n{hint}\n\n"
            "Контакты компании: +7 (777) 292-84-01, https://centr-krasok.kz/"
        )
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
