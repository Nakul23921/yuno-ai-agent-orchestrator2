from __future__ import annotations

import json
import mimetypes
import queue
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import ROOT, load_settings
from .llm import build_reasoner
from .runtime import AgentRuntime, EventHub, event_to_sse
from .storage import Store
from .telegram_channel import TelegramChannel
from .templates import TEMPLATES, seed_demo_data


class AppContext:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.store = Store(self.settings.database_path)
        seed_demo_data(self.store)
        self.hub = EventHub()
        self.runtime = AgentRuntime(self.store, build_reasoner(self.settings), self.hub)
        self.telegram = TelegramChannel(self.settings, self.runtime, self.store)
        self.runtime.start()
        self.telegram.start()


CTX: AppContext | None = None


class Handler(BaseHTTPRequestHandler):
    server_version = "YunoOrchestrator/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._json(self._state())
        elif parsed.path == "/api/events":
            self._sse()
        elif parsed.path == "/" or parsed.path.startswith("/static/"):
            self._static(parsed.path)
        else:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        data = self._body()
        if parsed.path == "/api/demo/seed":
            seed_demo_data(self.ctx.store)
            event = self.ctx.store.add_event(None, "demo.seeded", "Demo data seeded", {})
            self.ctx.hub.publish(event)
            self._json(self._state())
        elif parsed.path == "/api/agents":
            agent = self.ctx.store.upsert_agent(data)
            self._publish("agent.saved", f"Agent {agent['name']} saved", {"agent_id": agent["id"]})
            self._json(agent, HTTPStatus.CREATED)
        elif parsed.path.startswith("/api/workflows/") and parsed.path.endswith("/run"):
            workflow_id = parsed.path.split("/")[3]
            result = self.ctx.runtime.submit(workflow_id, data.get("input", ""), channel=data.get("channel", "web"))
            self._json({"run_id": result.run_id, "status": result.status})
        elif parsed.path == "/api/channel/local":
            workflow_id = data.get("workflow_id", "workflow-support")
            result = self.ctx.runtime.submit(workflow_id, data.get("message", ""), channel=data.get("channel", "telegram-simulator"))
            self._json({"run_id": result.run_id, "status": result.status, "channel": "telegram-simulator"})
        else:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        data = self._body()
        if parsed.path.startswith("/api/agents/"):
            data["id"] = parsed.path.split("/")[-1]
            agent = self.ctx.store.upsert_agent(data)
            self._publish("agent.updated", f"Agent {agent['name']} updated", {"agent_id": agent["id"]})
            self._json(agent)
        elif parsed.path.startswith("/api/workflows/"):
            data["id"] = parsed.path.split("/")[-1]
            workflow = self.ctx.store.upsert_workflow(data)
            self._publish("workflow.updated", f"Workflow {workflow['name']} updated", {"workflow_id": workflow["id"]})
            self._json(workflow)
        else:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/agents/"):
            agent_id = parsed.path.split("/")[-1]
            self.ctx.store.delete_agent(agent_id)
            self._publish("agent.deleted", f"Agent {agent_id} deleted", {"agent_id": agent_id})
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    @property
    def ctx(self) -> AppContext:
        assert CTX is not None
        return CTX

    def _state(self) -> dict[str, Any]:
        runs = self.ctx.store.list_runs()
        messages = self.ctx.store.list_messages()
        completed = [run for run in runs if run["status"] == "completed"]
        total_tokens = sum(run["token_count"] for run in runs)
        return {
            "agents": self.ctx.store.list_agents(),
            "workflows": self.ctx.store.list_workflows(),
            "runs": runs,
            "messages": messages,
            "events": self.ctx.store.list_events(),
            "templates": TEMPLATES,
            "settings": {
                "telegram_enabled": self.ctx.settings.enable_telegram and bool(self.ctx.settings.telegram_bot_token),
                "llm_provider": self.ctx.settings.llm_provider,
                "database_path": str(self.ctx.settings.database_path),
            },
            "metrics": {
                "agents": len(self.ctx.store.list_agents()),
                "workflows": len(self.ctx.store.list_workflows()),
                "messages": len(messages),
                "runs": len(runs),
                "completion_rate": round(len(completed) / len(runs), 2) if runs else 0,
                "total_tokens": total_tokens,
                "total_cost_cents": round(sum(run["cost_cents"] for run in runs), 4),
            },
        }

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str) -> None:
        rel = "index.html" if path == "/" else path.removeprefix("/static/")
        file_path = (ROOT / "static" / rel).resolve()
        if not str(file_path).startswith(str((ROOT / "static").resolve())) or not file_path.exists():
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = self.ctx.hub.subscribe()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    event = q.get(timeout=15)
                    self.wfile.write(event_to_sse(event))
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.ctx.hub.unsubscribe(q)

    def _publish(self, event_type: str, message: str, payload: dict[str, Any]) -> None:
        event = self.ctx.store.add_event(None, event_type, message, payload)
        self.ctx.hub.publish(event)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    global CTX
    CTX = AppContext()
    address = (CTX.settings.host, CTX.settings.port)
    server = ThreadingHTTPServer(address, Handler)
    print(f"Yuno Orchestrator running at http://{address[0]}:{address[1]}")
    print(f"SQLite database: {CTX.settings.database_path}")
    server.serve_forever()
