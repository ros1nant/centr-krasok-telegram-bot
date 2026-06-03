import re

# Темы вне компании — вежливый отказ без вызова модели (экономия + предсказуемость)
OFF_TOPIC_PATTERNS = [
    r"\b(погод|курс\s*(доллар|евро|биткоин)|рецепт|анекдот)\b",
    r"\b(напиши\s*код|python|javascript|sql\s*запрос)\b",
    r"\b(политик|войн[аы]|выборы)\b",
]

COMPANY_HINTS = [
    "центр красок",
    "centr-krasok",
    "краск",
    "колер",
    "dulux",
    "алмат",
    "астан",
    "доставк",
    "магазин",
    "бутик",
    "штукатур",
    "строител",
    "дизайн",
    "ваканс",
    "офис",
    "контакт",
    "бренд",
    "компани",
    "услуг",
    "продукт",
    "лкм",
    "wagner",
    "dufa",
]

FALLBACK_NO_INFO = (
    "У меня нет точной информации по этому вопросу в базе знаний. "
    "Пожалуйста, уточните у менеджеров: +7 (777) 292-84-01 или info@centr-krasok.kz, "
    "сайт https://centr-krasok.kz/"
)

OFF_TOPIC_REPLY = (
    "Я помогаю только с вопросами о компании «Центр Красок #1»: "
    "услуги, товары, салоны, доставка, программы для дизайнеров и строителей. "
    "Задайте, пожалуйста, вопрос о нашей компании."
)

# Признаки «галлюцинаций» — ответы, которые модель не должна давать
HALLUCINATION_MARKERS = [
    r"\b(openai|chatgpt|gpt-4)\b",
    r"\bмы\s+разрабатываем\s+(приложени|сайт|crm)\b",
    r"\bнаш\s+офис\s+в\s+(москв|санкт-петербург|европ)\b",
    r"\bваканси[яи]\s+(python|java|frontend)\s+разработчик\b",
]


def is_likely_off_topic(text: str) -> bool:
    lowered = text.lower().strip()
    if len(lowered) < 3:
        return False
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            return True
    if any(hint in lowered for hint in COMPANY_HINTS):
        return False
    # Короткие приветствия — не off-topic
    if lowered in {"привет", "здравствуйте", "hello", "hi", "добрый день", "start"}:
        return False
    # Длинный вопрос без намёка на компанию — мягкая эвристика
    if len(lowered) > 40 and not any(h in lowered for h in COMPANY_HINTS):
        return False
    return False


def sanitize_reply(reply: str, max_length: int) -> str:
    text = reply.strip()
    for pattern in HALLUCINATION_MARKERS:
        if re.search(pattern, text, re.IGNORECASE):
            return FALLBACK_NO_INFO
    if len(text) > max_length:
        text = text[: max_length - 3].rstrip() + "..."
    return text


def looks_like_refusal_needed(reply: str) -> bool:
    """Если модель сама признала незнание — оставляем как есть."""
    markers = ["нет точной информации", "нет информации", "не знаю", "не могу ответить"]
    lower = reply.lower()
    return any(m in lower for m in markers)
