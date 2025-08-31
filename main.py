import os
import logging
import re
import openai
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# === Конфиг из окружения / Render ===
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Set TELEGRAM_TOKEN and OPENAI_API_KEY in Environment variables.")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

SYSTEM_PROMPT = (
    "Ты — эмпатичный и поддерживающий чат-бот-психолог (КПТ). "
    "Всегда напоминай, что ты не настоящий психолог и при кризисе нужно обращаться к специалистам."
)

CRISIS_MESSAGE = (
    "⚠️ Похоже, вы говорите о причинении вреда себе. Я очень переживаю.\n\n"
    "Я всего лишь чат-бот и не могу оказать реальную помощь. Пожалуйста, обратитесь за срочной помощью.\n"
    "Россия: +7 (495) 989-50-50; 8 (800) 200-01-22\n"
    "Украина: 7333; Казахстан: 150; Беларусь: 8 (800) 100-16-11"
)

def check_for_crisis_keywords(text: str) -> bool:
    t = (text or "").lower()
    keys = [
        "суицид", "самоубийств", "покончить с собой", "убить себя",
        "хочу умереть", "не хочу жить", "наложить на себя руки",
        "повеситься", "вскрыть вены", "спрыгнуть"
    ]
    return any(k in t for k in keys)

# простая память диалога по пользователю
user_histories = {}

def start(update, context):
    uid = update.message.from_user.id
    user_histories[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]
    update.message.reply_text(
        "Здравствуйте! Я ваш КПТ-помощник. Помните: я не настоящий психолог. "
        "В кризисной ситуации обращайтесь к специалистам. Чем могу помочь?"
    )

def handle_message(update, context):
    uid = update.message.from_user.id
    text = update.message.text or ""

    if check_for_crisis_keywords(text):
        update.message.reply_text(CRISIS_MESSAGE)
        return

    if uid not in user_histories:
        user_histories[uid] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_histories[uid].append({"role": "user", "content": text})

    try:
        # Старый SDK (openai==0.28.1) — классический ChatCompletion
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",            # можно оставить gpt-4o-mini
            messages=user_histories[uid],
            temperature=0.7
        )
        bot_answer = resp["choices"][0]["message"]["content"]
        user_histories[uid].append({"role": "assistant", "content": bot_answer})
        update.message.reply_text(bot_answer)
    except Exception as e:
        logging.exception("OpenAI error")
        update.message.reply_text("Извините, случилась ошибка. Попробуйте позже.")

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    if WEBHOOK_URL:
        # секретный путь вебхука = токен
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN
        )
        full_url = f"{WEBHOOK_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        updater.bot.set_webhook(full_url)
        logging.info("Webhook set to %s", full_url)
        updater.idle()
    else:
        updater.start_polling()
        logging.info("Started with long polling")
        updater.idle()

if __name__ == "__main__":
    main()
