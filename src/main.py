import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import time
import logging

URL = "https://pass.rw.by/ru/route/"  # Сюда добавить параметры
TRAINS_TO_TRACK = {}
TELEGRAM_TOKEN = ""
CHAT_ID = ""
CHECK_INTERVAL = 10  # Интервал проверки в секундах

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


def check_trains(url, trains_to_track):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    trains = soup.find_all("div", class_="sch-table__row-wrap")

    available_trains = []
    for train in trains:
        train_number_span = train.find("span", class_="train-number")
        if train_number_span:
            train_number = train_number_span.text
            if train_number in trains_to_track:
                no_info = train.find("div", class_="sch-table__no-info")
                if not no_info:  # Если блока "Мест нет" нет, то места доступны
                    available_trains.append(train_number)

    return available_trains


async def send_telegram_notification(bot, chat_id, message):
    await bot.send_message(chat_id=chat_id, text=message)


async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    logger.info("Начало мониторинга...")

    while True:
        try:
            available_trains = check_trains(URL, TRAINS_TO_TRACK)
            if available_trains:
                message = (
                    f"Места доступны на следующие поезда: {', '.join(available_trains)}"
                )
                logger.info(message)
                await send_telegram_notification(bot, CHAT_ID, message)
            else:
                logger.info("Мест нет на отслеживаемые поезда.")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
