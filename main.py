WEBHOOK_URL = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", "10000"))


import openai
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
import re # Импортируем модуль для регулярных выражений

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = 'ВАШ_TELEGRAM_TOKEN'  # Вставьте сюда токен от BotFather
OPENAI_API_KEY = 'ВАШ_OPENAI_API_KEY' # Вставьте сюда ключ от OpenAI

openai.api_key = OPENAI_API_KEY

# Настройка логирования для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Тот самый системный промпт, определяющий личность бота
SYSTEM_PROMPT = """
Ты — эмпатичный и поддерживающий чат-бот-психолог, основанный на принципах когнитивно-поведенческой терапии (КПТ). Твоя задача — помогать пользователю исследовать свои мысли, эмоции и поведение.
Всегда используй сократический диалог: задавай наводящие вопросы, чтобы пользователь сам пришел к выводам.
Помогай выявлять когнитивные искажения (например, катастрофизацию, черно-белое мышление).
Предлагай простые КПТ-упражнения.
Сохраняй теплый, понимающий и неосуждающий тон.
В начале разговора обязательно напомни пользователю: "Пожалуйста, помните, что я — всего лишь программа, а не настоящий психолог. Я не могу оказать профессиональную помощь. В случае кризисной ситуации, пожалуйста, обратитесь к специалисту."
"""

# 🆘 НОВЫЙ БЛОК: Сообщение для кризисных ситуаций
CRISIS_MESSAGE = """
⚠️ Мне кажется, вы говорите о причинении вреда себе. Я очень обеспокоен(а) вашими словами.

Пожалуйста, помните, что я всего лишь чат-бот и не могу оказать реальную помощь. Очень важно, чтобы вы поговорили с кем-то прямо сейчас.

Вот контакты служб, куда можно обратиться за бесплатной и анонимной помощью:

**Россия:**
• Телефон доверия МЧС: +7 (495) 989-50-50
• Единый телефон доверия для детей и подростков: 8 (800) 200-01-22

**Украина:**
• Горячая линия "La Strada-Ukraine": 0 (800) 500-225 (или 116-111 с мобильного)
• Lifeline Ukraine: 7333

**Казахстан:**
• Национальная линия доверия для детей и молодежи: 150

**Беларусь:**
• Республиканская "Детская телефонная линия": 8 (800) 100-16-11

**Пожалуйста, позвоните. Ваша жизнь очень важна.**
"""

# 🆘 НОВЫЙ БЛОК: Функция для проверки на ключевые слова
def check_for_crisis_keywords(text):
    """Проверяет текст на наличие ключевых слов, связанных с суицидом."""
    # Приводим текст к нижнему регистру для простоты поиска
    text = text.lower()
    # Список ключевых слов и фраз. re.escape используется для экранирования спецсимволов
    keywords = [
        'суицид', 'самоубийств', 'покончить с собой', 'убить себя',
        'хочу умереть', 'не хочу жить', 'наложить на себя руки',
        'повеситься', 'вскрыть вены', 'спрыгнуть'
    ]
    # Проверяем, содержится ли хотя бы одно слово из списка в тексте
    for keyword in keywords:
        if keyword in text:
            return True
    return False

# Словарь для хранения истории диалогов с пользователями
user_histories = {}

def start(update, context):
    """Отправляет приветственное сообщение при команде /start"""
    user_id = update.message.from_user.id
    user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    welcome_message = "Здравствуйте! Я ваш КПТ-помощник. Чем я могу вам сегодня помочь?\n\nПожалуйста, помните, что я — всего лишь программа, а не настоящий психолог. В случае кризисной ситуации, обратитесь к специалисту."
    update.message.reply_text(welcome_message)

def handle_message(update, context):
    """Обрабатывает текстовые сообщения от пользователя"""
    user_id = update.message.from_user.id
    user_text = update.message.text

    # 🆘 ИЗМЕНЕНИЕ: Сначала проверяем сообщение на кризисные маркеры
    if check_for_crisis_keywords(user_text):
        update.message.reply_text(CRISIS_MESSAGE)
        return # Важно! Прерываем дальнейшую обработку сообщения

    # Если истории для этого пользователя нет, создаем ее
    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_histories[user_id].append({"role": "user", "content": user_text})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # или gpt-3.5-turbo
            messages=user_histories[user_id]
        )
        bot_response = response.choices[0].message['content']
        user_histories[user_id].append({"role": "assistant", "content": bot_response})
        update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI: {e}")
        update.message.reply_text("Извините, произошла ошибка. Пожалуйста, попробуйте позже.")

def main():
    """Основная функция для запуска бота"""
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    logging.info("Бот запущен...")
    updater.idle()

if __name__ == '__main__':
    main()