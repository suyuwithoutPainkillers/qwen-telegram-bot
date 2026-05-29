# Qwen Telegram Bot

A Telegram chatbot powered by Qwen through the DashScope OpenAI-compatible API.

## Features

- Direct Telegram private chat
- `/model` menu for Qwen model switching
- Admin-based access control
- SQLite-backed model selection and recent chat history
- Windows helper scripts for local proxy-based running
- Docker build support

## Environment Variables

| Variable | Description |
| --- | --- |
| `TELEGRAM_BOT_API_KEY` | Telegram Bot token from BotFather |
| `QWEN_API_KEY` or `DASHSCOPE_API_KEY` | Alibaba Cloud Model Studio / DashScope API key |
| `ADMIN_USER_IDS` | Telegram admin user IDs, comma-separated |
| `QWEN_BASE_URL` | Optional, defaults to `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `QWEN_MODELS` | Optional, comma-separated model menu |
| `TELEGRAM_PROXY` | Optional Telegram proxy, for example `http://127.0.0.1:7897` |

## Local Run

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

$env:TELEGRAM_BOT_API_KEY="your-telegram-token"
$env:QWEN_API_KEY="your-qwen-key"
$env:ADMIN_USER_IDS="your-telegram-user-id"
$env:TELEGRAM_PROXY="http://127.0.0.1:7897"
$env:HTTP_PROXY="http://127.0.0.1:7897"
$env:HTTPS_PROXY="http://127.0.0.1:7897"

.\.venv\Scripts\python.exe -u .\src\main.py --db-path .\data\bot.db
```

Windows users can also save `TELEGRAM_BOT_API_KEY`, `ADMIN_USER_IDS`, and `QWEN_API_KEY` as user environment variables and run:

```powershell
.\set_qwen_key_windows.ps1
.\run_bot_windows.ps1
```

`run_bot_windows.ps1` reads Windows environment variables first. If you are migrating from an old Docker setup, it also tries to read the Telegram token and admin IDs from a container named `tg_gpt_bot`.

## Docker

```bash
docker build -t qwen-telegram-bot .

docker run -d --restart=always \
  -v "$(pwd)/data:/app/data" \
  -e TELEGRAM_BOT_API_KEY="your-telegram-token" \
  -e QWEN_API_KEY="your-qwen-key" \
  -e ADMIN_USER_IDS="your-telegram-user-id" \
  -e TELEGRAM_PROXY="http://host.docker.internal:7897" \
  qwen-telegram-bot
```

## Commands

- `/start`: start the bot and show the model menu
- `/model`: switch models
- `/clear`: clear the current user's history
- `/access`: admin-only access list
- `/accessrequest`: admin-only access request toggle

## Security

Never commit real Telegram tokens, DashScope API keys, database files, logs, or `.env` files. The project `.gitignore` ignores `data/`, `logs/`, `.venv/`, and common local config files by default.

## License

MIT
