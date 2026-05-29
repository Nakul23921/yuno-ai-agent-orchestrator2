# Local Setup Guide

This project is designed to run on a normal personal laptop. It uses Python standard library modules plus SQLite, so there is no heavy install process.

## Laptop Requirements

Minimum:

- Windows 10/11, macOS, or Linux
- Python 3.11 or newer
- 4 GB RAM
- 1 GB free disk space
- Browser: Chrome, Edge, Firefox, or Safari

Recommended:

- 8 GB RAM or more
- Stable internet only if you want live Telegram or OpenAI mode

The default demo does not need OpenAI, LangChain, Docker, Postgres, Redis, or a GPU.

## Install Python On Windows

1. Download Python from `https://www.python.org/downloads/`.
2. During installation, check `Add python.exe to PATH`.
3. Open PowerShell and verify:

   ```powershell
   python --version
   ```

You should see Python 3.11 or newer.

If you see this message:

```text
Python was not found; run without arguments to install from the Microsoft Store...
```

then Windows is using the Microsoft Store shortcut instead of a real Python install. Install Python from `python.org`, check `Add python.exe to PATH`, close PowerShell, open a new PowerShell, and try again.

## Run The App

From the project folder:

```powershell
cd C:\Users\nakul\Documents\Codex\2026-05-24\files-mentioned-by-the-user-yuno
python run.py
```

Open this URL in your browser:

```text
http://127.0.0.1:8080
```

The terminal should keep running while you use the web UI.

Windows helper:

```powershell
.\scripts\run_windows.ps1
```

If PowerShell blocks `.ps1` scripts, run:

```powershell
.\scripts\run_windows.bat
```

## Run The Tests

Open another PowerShell window in the same folder:

```powershell
python -m unittest discover -s tests
```

Windows helper:

```powershell
.\scripts\test_windows.ps1
```

If PowerShell blocks `.ps1` scripts, run:

```powershell
.\scripts\test_windows.bat
```

Expected result:

```text
Ran 3 tests
OK
```

## Run The Main Demo

1. Open `http://127.0.0.1:8080`.
2. Go to `Workflows`.
3. Select `Customer Support Swarm`.
4. Run:

   ```text
   My order ORD-1024 is delayed and I want a refund.
   ```

5. Go to `Monitor`.
6. Show the live events, inter-agent messages, token count, and cost tracking.
7. Go to `Channel`.
8. Send:

   ```text
   My order ORD-1024 is delayed. Can you help and refund me?
   ```

This proves the local channel simulation, persisted message history, and multi-agent execution.

## Telegram Demo

For the strongest submission, show one real Telegram conversation.

1. Open Telegram.
2. Message `@BotFather`.
3. Create a bot.
4. Copy the bot token.
5. Create a local `.env` file in the project folder:

   ```text
   ENABLE_TELEGRAM=true
   TELEGRAM_BOT_TOKEN=<your-token>
   TELEGRAM_WORKFLOW_ID=workflow-support
   ```

   Do not commit `.env`; it is already ignored by `.gitignore`.

6. Verify the token:

   ```powershell
   python scripts/telegram_smoke_test.py
   ```

7. Start the app:

   ```powershell
   python run.py
   ```

8. Message your Telegram bot:

   ```text
   My order ORD-1024 is delayed. Can you help and refund me?
   ```

9. Show that the bot replies and the same trace appears in the web UI.

## Optional OpenAI Mode

Default mode is local and deterministic, so the demo works without paid API keys.

To use OpenAI:

```powershell
$env:YUNO_LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="<your-key>"
python run.py
```

If the OpenAI call fails, the app falls back to the local reasoner so the demo still works.
