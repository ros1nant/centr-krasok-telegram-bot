# AI Telegram Assistant — Центр Красок #1

MVP Telegram-бот с AI-ассистентом, который отвечает на вопросы о компании **на основе собранной базы знаний** (сайт [centr-krasok.kz](https://centr-krasok.kz/)).  
Интеграция с **Ollama** (локально) или **Google Gemini** (облако, API-ключ).

## Возможности

- Обычный чат **без команд и меню** (кроме скрытого `/start` при первом открытии)
- Ответы только по базе знаний `data/company_knowledge.md`
- **Контекст диалога** — последние N сообщений на пользователя
- **Защита от галлюцинаций**: низкая temperature, system prompt, фильтры off-topic и маркеров выдумок
- Шаблон настроек `env.template` (в git), секреты в `.env` (не в git)

## Быстрый старт

### 1. Выбрать LLM

**Вариант A — Ollama (локально, без API-ключа):**

1. https://ollama.com → установить и запустить  
2. `ollama pull llama3.2`  
3. В `.env`: `LLM_PROVIDER=ollama`

**Вариант B — Google Gemini (облако):**

1. Ключ: https://aistudio.google.com/apikey  
2. В `.env`:
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=ваш_ключ
   GEMINI_MODEL=gemini-2.0-flash
   ```
3. Ollama **не нужна**

### 2. Создать Telegram-бота

1. В Telegram открыть [@BotFather](https://t.me/BotFather)  
2. `/newbot` → получить **токен**

### 3. Настроить проект

```powershell
cd c:\Users\ASUS\Desktop\testproject
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy env.template .env
```

**PowerShell:** если `activate` выдаёт ошибку про Execution Policy — **не активируйте venv**, вызывайте Python так:

```powershell
.venv\Scripts\python.exe main.py
```

Либо один раз разрешите скрипты только для вашего пользователя:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\activate
```

Либо в **cmd** (не PowerShell): `.venv\Scripts\activate.bat`

Отредактировать `.env`:

| Переменная | Куда вставить |
|------------|----------------|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather |
| `LLM_PROVIDER` | `ollama` или `gemini` |
| `GEMINI_API_KEY` | Только для Gemini |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Только для Ollama |

### 4. Запуск

```powershell
cd c:\Users\ASUS\Desktop\testproject
.venv\Scripts\python.exe main.py
```

Напишите боту в Telegram: *«Чем занимается компания?»*, *«Где офис в Алматы?»*.

## Структура проекта

```
testproject/
├── data/
│   └── company_knowledge.md   # Структурированная база о компании
├── src/
│   ├── bot.py                 # Telegram-логика
│   ├── ai_client.py           # Ollama + Gemini
│   ├── knowledge.py           # System prompt + база
│   ├── context_manager.py     # История диалога
│   ├── guardrails.py          # Off-topic и санитизация
│   └── config.py              # Переменные окружения
├── main.py
├── env.template               # Шаблон (в git, без секретов)
└── requirements.txt
```

## Где оставить токены

Файл **`.env`** (создаётся из `env.template`, в git не попадает):

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdef...

# Gemini:
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash

# или Ollama:
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.2
```

**Не коммитьте `.env` в git** — он в `.gitignore`.

## LLM API

| Провайдер | Переключатель | Документация |
|-----------|---------------|--------------|
| Ollama | `LLM_PROVIDER=ollama` | `POST /api/chat` |
| Gemini | `LLM_PROVIDER=gemini` | [Gemini API](https://ai.google.dev/gemini-api/docs) |

Общие параметры: `temperature: 0.3`, system prompt с базой знаний.

## Примеры вопросов

- Чем занимается компания?
- Какие услуги предоставляет?
- Где находится офис?
- Какие бренды есть в каталоге?
- Кто клиенты компании?
- Есть ли вакансии?
- Как связаться с менеджером?

## Ограничения MVP

- Контекст хранится в памяти (сбрасывается при перезапуске бота)
- Цены и остатки не отдаются — только направление на сайт
- Для продакшена: Redis для контекста, rate limit, логирование, healthcheck

## Лицензия

Учебный / тестовый проект.
