from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

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
    response = requests.get(url, headers={"User-Agent": USER_AGENT})
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

        departure = row.find("div", class_="train-from-time").text.strip()
        arrival = row.find("div", class_="train-to-time").text.strip()
        duration = row.find("div", class_="train-duration-time").text.strip()

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
