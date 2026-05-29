from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_env_file() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env_file()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("TELEGRAM_BOT_TOKEN is missing. Put it in .env or set it in PowerShell.")
        return 1
    url = f"https://api.telegram.org/bot{token}/getMe"
    with urllib.request.urlopen(url, timeout=20) as res:
        data = json.loads(res.read().decode("utf-8"))
    if not data.get("ok"):
        print(json.dumps(data, indent=2))
        return 1
    bot = data["result"]
    print(f"Telegram bot connected: @{bot.get('username')} ({bot.get('first_name')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
