import asyncio
import logging
import os
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

load_dotenv()

import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)
DEFAULT_INTERVAL = 10


@dataclass
class SeatClass:
    name: str
    count: int
    price_byn: str


@dataclass
class TrainInfo:
    number: str
    departure: str
    arrival: str
    duration: str
    seats: list[SeatClass]


def fetch_page(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.text


def parse_trains(
    html: str, train_filter: set[str] | None = None
) -> list[TrainInfo]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("div", class_="sch-table__row-wrap")
    trains = []

    for row in rows:
        if row.find("div", class_="sch-table__no-info"):
            continue

        number_el = row.find("span", class_="train-number")
        if not number_el:
            continue
        number = number_el.text.strip()

        if train_filter and number not in train_filter:
            continue

        dep_el = row.find("div", class_="train-from-time")
        arr_el = row.find("div", class_="train-to-time")
        dur_el = row.find("div", class_="train-duration-time")
        if not dep_el or not arr_el or not dur_el:
            continue
        departure = dep_el.text.strip()
        arrival = arr_el.text.strip()
        duration = dur_el.text.strip()

        seats = []
        for item in row.find_all("div", class_="sch-table__t-item"):
            name_el = item.find("div", class_="sch-table__t-name")
            name = name_el.text.strip() if name_el else ""
            if not name:
                continue

            count_el = item.find("a", class_="sch-table__t-quant")
            count_span = count_el.find("span") if count_el else None
            count = int(count_span.text.strip()) if count_span else 0

            prices = [
                el["data-cost-byn"]
                for el in item.select("span.js-price[data-cost-byn]")
            ]
            if prices:
                price = min(prices, key=lambda p: float(p.replace(",", ".")))
            else:
                price = "—"

            seats.append(SeatClass(name=name, count=count, price_byn=price))

        if seats:
            trains.append(
                TrainInfo(
                    number=number,
                    departure=departure,
                    arrival=arrival,
                    duration=duration,
                    seats=seats,
                )
            )

    return trains


def parse_watch_url(url: str) -> dict | None:
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if parsed.hostname != "pass.rw.by":
        return None
    params = parse_qs(parsed.query)
    if "from" not in params or "to" not in params:
        return None
    return {
        "url": url,
        "from": params["from"][0],
        "to": params["to"][0],
        "date": params.get("date", [""])[0],
    }


def filter_new_trains(
    trains: list[TrainInfo], notified: set[str]
) -> tuple[list[TrainInfo], set[str]]:
    current = {t.number for t in trains}
    updated = notified & current
    new = [t for t in trains if t.number not in notified]
    updated.update(t.number for t in new)
    return new, updated


def format_notification(
    trains: list[TrainInfo], from_city: str, to_city: str
) -> str:
    lines = ["🚂 Места появились!"]
    for train in trains:
        lines.append("")
        lines.append(f"🔹 Поезд {train.number}")
        lines.append(f"📍 {from_city} → {to_city}")
        lines.append(f"🕐 {train.departure} → {train.arrival} ({train.duration})")
        for seat in train.seats:
            lines.append(
                f"💺 {seat.name} — {seat.count} мест — от {seat.price_byn} BYN"
            )
    return "\n".join(lines)


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    jobs = context.job_queue.get_jobs_by_name(name)
    for job in jobs:
        job.schedule_removal()
    return bool(jobs)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🚂 Монитор билетов pass.rw.by\n\n"
        "Команды:\n"
        "/watch <url> [поезда] — начать мониторинг\n"
        "/stop — остановить\n"
        "/interval <сек> — изменить интервал\n"
        "/status — текущий статус\n\n"
        "Пример:\n"
        "/watch https://pass.rw.by/ru/route/?from=... 747Б,709Б"
    )
    await update.message.reply_text(text)


async def cmd_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "❌ Использование:\n/watch <url> 747Б,709Б\n\nСкопируйте ссылку из pass.rw.by"
        )
        return

    url = context.args[0]
    info = parse_watch_url(url)
    if not info:
        await update.message.reply_text(
            "❌ Неверная ссылка. Скопируйте URL из pass.rw.by"
        )
        return

    train_filter = None
    if len(context.args) > 1:
        train_filter = set(context.args[1].split(","))

    chat_id = update.effective_chat.id
    interval = context.chat_data.get("interval", DEFAULT_INTERVAL)

    context.chat_data.update(
        {
            "url": info["url"],
            "from": info["from"],
            "to": info["to"],
            "date": info["date"],
            "train_filter": train_filter,
            "notified_trains": set(),
            "consecutive_errors": 0,
            "interval": interval,
        }
    )

    remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_repeating(
        check_job,
        interval=interval,
        first=5,
        chat_id=chat_id,
        name=str(chat_id),
    )

    trains_text = (
        ", ".join(sorted(train_filter)) if train_filter else "Все поезда"
    )
    text = (
        f"✅ Мониторинг запущен (каждые {interval} сек)\n"
        f"📍 {info['from']} → {info['to']}, {info['date']}\n"
        f"🔍 Поезда: {trains_text}"
    )
    await update.message.reply_text(text)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    removed = remove_job_if_exists(str(chat_id), context)
    context.chat_data.clear()
    text = "⏹ Мониторинг остановлен" if removed else "ℹ️ Нет активного мониторинга"
    await update.message.reply_text(text)


async def cmd_interval(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat_id = update.effective_chat.id
    if "url" not in context.chat_data:
        await update.message.reply_text("❌ Нет активного мониторинга")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Использование: /interval <секунды>")
        return

    new_interval = int(context.args[0])
    if new_interval < 1:
        await update.message.reply_text("❌ Минимальный интервал: 1 секунда")
        return
    context.chat_data["interval"] = new_interval

    remove_job_if_exists(str(chat_id), context)
    context.job_queue.run_repeating(
        check_job,
        interval=new_interval,
        first=new_interval,
        chat_id=chat_id,
        name=str(chat_id),
    )

    await update.message.reply_text(f"✅ Интервал изменён на {new_interval} сек")


async def cmd_status(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if "url" not in context.chat_data:
        await update.message.reply_text("ℹ️ Нет активного мониторинга")
        return

    data = context.chat_data
    trains_text = (
        ", ".join(sorted(data["train_filter"]))
        if data.get("train_filter")
        else "Все"
    )
    text = (
        f"📊 Статус мониторинга\n"
        f"📍 {data['from']} → {data['to']}, {data['date']}\n"
        f"🔍 Поезда: {trains_text}\n"
        f"⏱ Интервал: {data['interval']} сек"
    )
    await update.message.reply_text(text)


async def check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    data = context.chat_data

    url = data.get("url")
    if not url:
        return

    try:
        html = await asyncio.to_thread(fetch_page, url)
        data["consecutive_errors"] = 0
    except Exception as e:
        data["consecutive_errors"] = data.get("consecutive_errors", 0) + 1
        logger.error(f"Ошибка при запросе: {e}")
        if data["consecutive_errors"] == 5:
            await context.bot.send_message(
                chat_id=chat_id, text=f"⚠️ Не удалось проверить: {e}"
            )
        return

    trains = parse_trains(html, data.get("train_filter"))
    notified = data.get("notified_trains", set())
    new_trains, updated_notified = filter_new_trains(trains, notified)
    data["notified_trains"] = updated_notified

    if new_trains:
        msg = format_notification(new_trains, data["from"], data["to"])
        await context.bot.send_message(chat_id=chat_id, text=msg)
    else:
        logger.info("Мест нет на отслеживаемые поезда.")


def main() -> None:
    token = os.environ["TELEGRAM_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("watch", cmd_watch))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("interval", cmd_interval))
    app.add_handler(CommandHandler("status", cmd_status))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
