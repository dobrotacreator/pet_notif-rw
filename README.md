# notifrw

Telegram bot that monitors train ticket availability on pass.rw.by (Belarusian Railways). Sends a notification when seats become available.

## Features

- Controlled entirely via Telegram commands — no code edits needed
- Rich notifications with seat types and prices
- Notifies only when seats appear (no spam)
- Configurable check interval

## Setup

```bash
uv sync
```

Create a `.env` file:

```
TELEGRAM_TOKEN=your_bot_token
```

## Usage

```bash
uv run python src/notifrw/main.py
```

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Show help |
| `/watch <url> [trains]` | Start monitoring. URL from pass.rw.by, optional comma-separated train filter |
| `/stop` | Stop monitoring |
| `/interval <sec>` | Change check interval (default: 10s) |
| `/status` | Show current config |

### Example

```
/watch https://pass.rw.by/ru/route/?from=Гомель&to=Минск&date=2026-03-29 747Б,709Б
```
