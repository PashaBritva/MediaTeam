import json
import schedule
import time
import threading
import telebot
from datetime import datetime, timedelta
import locale
import os
import re
import logging
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO, filename="info.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")

locale.setlocale(
    category=locale.LC_ALL,
    locale="Russian"
)

# Инициализация бота
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))

team_data = []


# Загружаем данные о команде
def load_data():
    global team_data
    with open("./data/team.json", "r", encoding="utf-8") as file:
        team_data = json.load(file)


load_data()


# Функция для сохранения данных
def save_data():
    with open("./data/team.json", "w", encoding="utf-8") as File:
        json.dump(team_data, File, ensure_ascii=False, indent=4)


# Функция для выбора операторов
def get_operators():
    operators = team_data["operators"]
    last_operators = team_data["last_operators"]

    if not last_operators:
        selected = operators[:2]
    else:
        remaining_operator = last_operators[1]
        index = operators.index(remaining_operator)
        next_operator = operators[(index + 1) % len(operators)]
        selected = [remaining_operator, next_operator]

    team_data["last_operators"] = selected
    save_data()
    return selected


# Функция для выбора звукорежиссера
def get_sound_operator():
    sound_operators = team_data["sound_operators"]
    last_sound_operator = team_data.get("last_sound_operator")

    if last_sound_operator:
        index = sound_operators.index(last_sound_operator)
        selected = sound_operators[(index + 1) % len(sound_operators)]
    else:
        selected = sound_operators[0]

    team_data["last_sound_operator"] = selected
    save_data()
    return selected


# Функция для выбора видеорежиссера
def get_video_operator():
    video_operators = team_data["video_operators"]
    last_video_operator = team_data.get("last_video_operator")
    operator_day_count = team_data.get("operator_day_count", 0)

    if last_video_operator and operator_day_count < 2:
        selected = last_video_operator
        team_data["operator_day_count"] = operator_day_count + 1
    else:
        if last_video_operator:
            index = video_operators.index(last_video_operator)
            selected = video_operators[(index + 1) % len(video_operators)]
        else:
            selected = video_operators[0]
        team_data["last_video_operator"] = selected
        team_data["operator_day_count"] = 1

    save_data()
    return selected


# Функция для выбора оператора слов
def get_word_operator():
    word_operators = team_data["word_operators"]
    last_word_operator = team_data.get("last_word_operator")
    word_operator_day_count = team_data.get("word_operator_day_count", 0)

    if last_word_operator and word_operator_day_count < 3:
        selected = last_word_operator
        team_data["word_operator_day_count"] = word_operator_day_count + 1
    else:
        if last_word_operator:
            index = word_operators.index(last_word_operator)
            selected = word_operators[(index + 1) % len(word_operators)]
        else:
            selected = word_operators[0]
        team_data["last_video_operator"] = selected
        team_data["operator_day_count"] = 1

    save_data()
    return selected


# Функция для формирования сообщения
def generate_schedule():
    today = datetime.now()
    next_sunday = today + timedelta(days=(6 - today.weekday()))
    date_str = next_sunday.strftime("%d %B")

    if team_data["day"] == 0 and today != next_sunday:
        operators = get_operators()
        sound_operator = get_sound_operator()
        video_operator = get_video_operator()
        team_data["day"] = 1
        save_data()
    else:
        if team_data["next_sunday"] < today.weekday():
            team_data["day"] = 0
            team_data["next_sunday"] = next_sunday
            save_data()

        operators = team_data["last_operators"]
        sound_operator = team_data.get("last_sound_operator")
        video_operator = team_data.get("last_video_operator")

    message = (
        f"📅 Расписание на {date_str}:\n\n"
        f"  🎤 Операторы:\n"
        f"      ● @{operators[0].split('-')[1]} *{operators[0].split('-')[0]}*\n"
        f"      ● @{operators[1].split('-')[1]} *{operators[1].split('-')[0]}*\n\n"
        f"  🎧 Звукорежиссер:\n"
        f"      ● @{sound_operator.split('-')[1]} *{sound_operator.split('-')[0]}*\n\n"
        f"  🎥 Видеорежиссер:\n"
        f"      ● @{video_operator.split('-')[1]} *{video_operator.split('-')[0]}*\n"
    )
    return message


# Функция для отправки сообщения
def send_schedule():
    message = generate_schedule()
    bot.send_message(os.getenv("GROUP_ID"), message)


# Планировщик задач
def run_scheduler():
    schedule.every().friday.at("09:00").do(send_schedule)
    schedule.every().saturday.at("14:00").do(send_schedule)

    while True:
        schedule.run_pending()
        time.sleep(3)


def escape_markdown_v2(text):
    escape_chars = r'_[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


# Команда для ручной проверки
@bot.message_handler(commands=["start", "shed"])
def start(message):
    global team_data

    user_id = message.from_user.id
    chat_id = message.chat.id

    if str(chat_id) != str(os.getenv("GROUP_ID")) and str(chat_id) != str('-1002493957985'):
        return

    now = time.time()
    last_time = team_data.get("last_command_time", 0)

    time_left = max(0, team_data["cooldown"] - (now - last_time))
    if time_left > 0:
        msg = bot.send_message(chat_id, f"⏳ Подождите {int(time_left)} секунд перед повторным вызовом команды.", disable_notification=True)

        while time_left > 0:
            time.sleep(1)
            time_left = max(0, team_data["cooldown"] - (time.time() - last_time))
            try:
                bot.edit_message_text(f"⏳ Подождите {int(time_left)} секунд перед повторным вызовом команды.",
                                      chat_id, msg.message_id)
            except Exception:
                break

        bot.edit_message_text(escape_markdown_v2(generate_schedule()), message.chat.id, msg.message_id, parse_mode="Markdown")
        return

    team_data["last_command_time"] = now
    save_data()

    msg = escape_markdown_v2(generate_schedule())
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", disable_notification=True)


if __name__ == "__main__":
    print(f"Бот @{bot.get_me().username} запущен!")
    logging.info(f"Bot @{bot.get_me().username} starting...!")
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    bot.polling(none_stop=True, skip_pending=True)
