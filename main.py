# main.py
import os
import re
import logging
import openai
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import BadRequest

# -------------------- Конфиг из окружения --------------------
TELEGRAM_TOKEN = os.getenv("8430427231:AAGD49Ns1XEkFH6wHKg0HNk1Vkw0VVKAjhE")
OPENAI_API_KEY = os.getenv("")

# Базовый публичный URL приложения (Render подставляет RENDER_EXTERNAL_URL)
WEBHOOK_BASE = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL") or ""
# Срежем любой явный :порт (Telegram принимает вебхуки только на 80/88/443/8443)
WEBHOOK_BASE = re.sub(r":\d+(?=/|$)", "", WEBHOOK_BASE).rstrip("/")
PORT = int(os.getenv("PORT", "10000"))  # внутренний порт Render

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Нужно задать переменные окружения TELEGRAM_TOKEN и OPENAI_API_KEY.")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bot")

# -------------------- Тексты --------------------
SYSTEM_PROMPT = (
    "Ты — эмпатичный чат-бот-психолог (КПТ). Помогай мягко и бережно, "
    "используй сократические вопросы, напоминай, что ты не заменяешь специалиста. "
    "При признаках кризиса направляй к горячим линиям."
)

CRISIS_MESSAGE = (
    "⚠️ Похоже, вы говорите о причинении вреда себе. Я переживаю за вас.\n\n"
    "Я всего лишь чат-бот и не могу оказать реальную помощь. Пожалуйста, обратитесь за срочной помощью:\n"
    "Россия: +7 (495) 989-50-50; 8 (800) 200-01-22\n"
    "Украина: 7333; Казахстан: 150; Беларусь: 8 (800) 100-16-11"
)

def check_for_crisis_keywords(text: str) -> bool:
    t = (text or "").lower()
    keys = [
        "суицид", "самоубийств", "покончить с собой", "убить себя",
        "хочу умереть", "не хочу жить", "наложить на себя руки",
        "повеситься", "вскрыть вены", "спрыгнуть",
    ]
    return any(k in t for k in keys)

# Память диалога на время жизни процесса
user_histories = {}

# -------------------- Хендлеры --------------------
def start(update, context):
    uid = update.effective_user.id
    user_histories[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
    update.message.reply_text(
        "Привет! Я КПТ-помощник. Помните: я не заменяю психолога. В кризисе — обратитесь к специалистам.\n"
        "О чём хотите поговорить?"
    )

def handle_message(update, context):
    uid = update.effective_user.id
    text = update.message.text or ""

    if check_for_crisis_keywords(text):
        update.message.reply_text(CRISIS_MESSAGE)
        return

    if uid not in user_histories:
        user_histories[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_histories[uid].append({"role": "user", "content": text})

    try:
        # openai==0.28.1
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=user_histories[uid],
            temperature=0.7,
        )
        answer = resp["choices"][0]["message"]["content"]
        user_histories[uid].append({"role": "assistant", "content": answer})
        update.message.reply_text(answer)
    except Exception as e:
        log.exception("OpenAI error")
        update.message.reply_text("Извините, произошла ошибка. Попробуйте позже.")

# -------------------- Запуск --------------------
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    if WEBHOOK_BASE:
        # собственный маленький HTTP-сервер PTB
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,  # секретный путь = токен
        )
        full_url = f"{WEBHOOK_BASE}/{TELEGRAM_TOKEN}"
        try:
            updater.bot.delete_webhook()  # на всякий случай очистим старый
        except Exception:
            pass
        try:
            updater.bot.set_webhook(full_url)
            log.info("Webhook set to %s", full_url)
        except BadRequest as e:
            log.error("Failed to set webhook: %s", e)
            raise
        updater.idle()
    else:
        # Фолбэк на long polling (локально)
        log.warning("WEBHOOK_BASE пуст. Запускаю long polling.")
        updater.start_polling()
        updater.idle()

if __name__ == "__main__":
    main()

