import json
import schedule
import time
import threading
import telebot
from datetime import datetime, timedelta
import os


import logging
logging.basicConfig(level=logging.INFO, filename="info.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")


# Загружаем данные о команде
with open("data/team.json", "r", encoding="utf-8") as file:
    team_data = json.load(file)

# Инициализация бота
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))

# Функция для сохранения данных
def save_data():
    with open("data/teams.json", "w", encoding="utf-8") as file:
        json.dump(team_data, file, ensure_ascii=False, indent=4)

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
    else:
        if team_data["next_sunday"] < today.weekday():
            team_data["day"] = 0
            team_data["next_sunday"] = next_sunday

        operators = team_data["last_operators"]
        sound_operator = team_data.get("last_sound_operator")
        video_operator = team_data.get("last_video_operator")


    message = (
        f"📅 Расписание на {date_str}:\n\n"
        f"  🎤 Операторы:\n"
        f"      ● {operators[0]}\n"
        f"      ● {operators[1]}\n\n"
        f"  🎧 Звукорежиссер:\n"
        f"      ● {sound_operator}\n\n"
        f"  🎥 Видеорежиссер:\n"
        f"      ● {video_operator}"
    )
    return message

# Функция для отправки сообщения
def send_schedule():
    message = generate_schedule()
    bot.send_message(os.getenv("GROU_ID"), message)

# Планировщик задач
def run_scheduler():
    schedule.every().friday.at("09:00").do(send_schedule)
    schedule.every().saturday.at("14:00").do(send_schedule)

    while True:
        schedule.run_pending()
        time.sleep(10)

# Команда для ручной проверки
@bot.message_handler(commands=["start"])
def start(message):
    msg = generate_schedule()
    bot.send_message(message.chat.id, msg)

# Запуск бота
if __name__ == "__main__":
    try:
        print(f"Бот @{bot.get_me().username} запущен!")
        logging.info(f"Bot @{bot.get_me().username} starting...!")
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.start()

        bot.polling(none_stop=True, skip_pending=True)
    except Exception as e:
        logging.exception(e)
        print(e)