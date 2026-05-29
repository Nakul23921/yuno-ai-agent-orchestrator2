from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

from .config import Settings
from .runtime import AgentRuntime
from .storage import Store


class TelegramChannel:
    def __init__(self, settings: Settings, runtime: AgentRuntime, store: Store):
        self.settings = settings
        self.runtime = runtime
        self.store = store
        self._offset = 0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if not self.settings.enable_telegram or not self.settings.telegram_bot_token:
            self.store.add_event(None, "channel.telegram.disabled", "Telegram disabled; use the web channel simulator or set TELEGRAM_BOT_TOKEN.", {})
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="telegram-channel")
        self._thread.start()
        self.store.add_event(None, "channel.telegram.started", "Telegram polling started", {"workflow_id": self.settings.telegram_workflow_id})

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                updates = self._api("getUpdates", {"timeout": 20, "offset": self._offset + 1})
                for update in updates.get("result", []):
                    self._offset = max(self._offset, int(update["update_id"]))
                    self._handle_update(update)
            except Exception as exc:  # noqa: BLE001 - long-running channel should recover
                self.store.add_event(None, "channel.telegram.error", str(exc), {})
                time.sleep(5)

    def _handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id")
        if not text or not chat_id:
            return
        if text.startswith("/start"):
            self._send(chat_id, "Yuno Orchestrator is online. Send an order issue like: My order ORD-1024 is delayed, can I get a refund?")
            return
        self.store.add_event(None, "channel.telegram.received", "Telegram message received", {"chat_id": chat_id, "text": text})
        self.runtime.submit(
            self.settings.telegram_workflow_id,
            text,
            channel="telegram",
            external_reply=lambda response: self._send(chat_id, response),
        )

    def _send(self, chat_id: int, text: str) -> None:
        self._api("sendMessage", {"chat_id": chat_id, "text": text[:3900]})

    def _api(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        base = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/{method}"
        data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(base, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
