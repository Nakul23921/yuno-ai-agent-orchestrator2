from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        with self._lock:
            self.conn.executescript(
                """
                pragma journal_mode = WAL;
                create table if not exists agents (
                    id text primary key,
                    name text not null,
                    role text not null,
                    system_prompt text not null,
                    model text not null,
                    tools text not null,
                    channels text not null,
                    schedules text not null,
                    memory text not null,
                    skills text not null,
                    interaction_rules text not null,
                    guardrails text not null,
                    created_at text not null,
                    updated_at text not null
                );
                create table if not exists workflows (
                    id text primary key,
                    name text not null,
                    description text not null,
                    template_key text,
                    nodes text not null,
                    edges text not null,
                    created_at text not null,
                    updated_at text not null
                );
                create table if not exists runs (
                    id text primary key,
                    workflow_id text not null,
                    status text not null,
                    input text not null,
                    output text not null default '',
                    token_count integer not null default 0,
                    cost_cents real not null default 0,
                    started_at text not null,
                    ended_at text
                );
                create table if not exists messages (
                    id text primary key,
                    run_id text,
                    workflow_id text,
                    agent_id text,
                    sender text not null,
                    recipient text not null,
                    channel text not null,
                    content text not null,
                    metadata text not null,
                    created_at text not null
                );
                create table if not exists events (
                    id integer primary key autoincrement,
                    run_id text,
                    type text not null,
                    message text not null,
                    payload text not null,
                    created_at text not null
                );
                """
            )
            self.conn.commit()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def upsert_agent(self, data: dict[str, Any]) -> dict[str, Any]:
        agent_id = data.get("id") or new_id("agent")
        existing = self.get_agent(agent_id)
        created_at = existing["created_at"] if existing else now_iso()
        row = {
            "id": agent_id,
            "name": data["name"],
            "role": data["role"],
            "system_prompt": data["system_prompt"],
            "model": data.get("model", "local-reasoner"),
            "tools": json.dumps(data.get("tools", [])),
            "channels": json.dumps(data.get("channels", [])),
            "schedules": json.dumps(data.get("schedules", [])),
            "memory": json.dumps(data.get("memory", {})),
            "skills": json.dumps(data.get("skills", [])),
            "interaction_rules": json.dumps(data.get("interaction_rules", [])),
            "guardrails": json.dumps(data.get("guardrails", [])),
            "created_at": created_at,
            "updated_at": now_iso(),
        }
        with self._lock:
            self.conn.execute(
                """
                insert into agents values (
                    :id, :name, :role, :system_prompt, :model, :tools, :channels,
                    :schedules, :memory, :skills, :interaction_rules, :guardrails,
                    :created_at, :updated_at
                )
                on conflict(id) do update set
                    name=excluded.name, role=excluded.role,
                    system_prompt=excluded.system_prompt, model=excluded.model,
                    tools=excluded.tools, channels=excluded.channels,
                    schedules=excluded.schedules, memory=excluded.memory,
                    skills=excluded.skills, interaction_rules=excluded.interaction_rules,
                    guardrails=excluded.guardrails, updated_at=excluded.updated_at
                """,
                row,
            )
            self.conn.commit()
        return self.get_agent(agent_id)

    def delete_agent(self, agent_id: str) -> None:
        with self._lock:
            self.conn.execute("delete from agents where id = ?", (agent_id,))
            self.conn.commit()

    def upsert_workflow(self, data: dict[str, Any]) -> dict[str, Any]:
        workflow_id = data.get("id") or new_id("workflow")
        existing = self.get_workflow(workflow_id)
        created_at = existing["created_at"] if existing else now_iso()
        row = {
            "id": workflow_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "template_key": data.get("template_key"),
            "nodes": json.dumps(data.get("nodes", [])),
            "edges": json.dumps(data.get("edges", [])),
            "created_at": created_at,
            "updated_at": now_iso(),
        }
        with self._lock:
            self.conn.execute(
                """
                insert into workflows values (
                    :id, :name, :description, :template_key, :nodes, :edges, :created_at, :updated_at
                )
                on conflict(id) do update set
                    name=excluded.name, description=excluded.description,
                    template_key=excluded.template_key, nodes=excluded.nodes,
                    edges=excluded.edges, updated_at=excluded.updated_at
                """,
                row,
            )
            self.conn.commit()
        return self.get_workflow(workflow_id)

    def create_run(self, workflow_id: str, user_input: str) -> dict[str, Any]:
        run = {
            "id": new_id("run"),
            "workflow_id": workflow_id,
            "status": "queued",
            "input": user_input,
            "output": "",
            "token_count": 0,
            "cost_cents": 0,
            "started_at": now_iso(),
            "ended_at": None,
        }
        with self._lock:
            self.conn.execute(
                "insert into runs values (:id,:workflow_id,:status,:input,:output,:token_count,:cost_cents,:started_at,:ended_at)",
                run,
            )
            self.conn.commit()
        return run

    def update_run(self, run_id: str, **changes: Any) -> dict[str, Any]:
        if not changes:
            return self.get_run(run_id)
        assignments = ", ".join(f"{key}=?" for key in changes)
        values = list(changes.values()) + [run_id]
        with self._lock:
            self.conn.execute(f"update runs set {assignments} where id = ?", values)
            self.conn.commit()
        return self.get_run(run_id)

    def add_message(self, data: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": data.get("id") or new_id("msg"),
            "run_id": data.get("run_id"),
            "workflow_id": data.get("workflow_id"),
            "agent_id": data.get("agent_id"),
            "sender": data["sender"],
            "recipient": data["recipient"],
            "channel": data.get("channel", "internal"),
            "content": data["content"],
            "metadata": json.dumps(data.get("metadata", {})),
            "created_at": now_iso(),
        }
        with self._lock:
            self.conn.execute(
                "insert into messages values (:id,:run_id,:workflow_id,:agent_id,:sender,:recipient,:channel,:content,:metadata,:created_at)",
                row,
            )
            self.conn.commit()
        return self._decode(row)

    def add_event(self, run_id: str | None, event_type: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        row = {
            "run_id": run_id,
            "type": event_type,
            "message": message,
            "payload": json.dumps(payload or {}),
            "created_at": now_iso(),
        }
        with self._lock:
            cur = self.conn.execute(
                "insert into events (run_id,type,message,payload,created_at) values (:run_id,:type,:message,:payload,:created_at)",
                row,
            )
            self.conn.commit()
            row["id"] = cur.lastrowid
        return self._decode(row)

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        return self._one("select * from agents where id = ?", (agent_id,))

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        return self._one("select * from workflows where id = ?", (workflow_id,))

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self._one("select * from runs where id = ?", (run_id,))

    def list_agents(self) -> list[dict[str, Any]]:
        return self._many("select * from agents order by updated_at desc", ())

    def list_workflows(self) -> list[dict[str, Any]]:
        return self._many("select * from workflows order by updated_at desc", ())

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._many("select * from runs order by started_at desc limit ?", (limit,))

    def list_messages(self, limit: int = 80) -> list[dict[str, Any]]:
        return self._many("select * from messages order by created_at desc limit ?", (limit,))

    def list_events(self, limit: int = 80) -> list[dict[str, Any]]:
        return self._many("select * from events order by id desc limit ?", (limit,))

    def _one(self, sql: str, args: tuple[Any, ...]) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute(sql, args).fetchone()
        return self._decode(dict(row)) if row else None

    def _many(self, sql: str, args: tuple[Any, ...]) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.conn.execute(sql, args).fetchall()
        return [self._decode(dict(row)) for row in rows]

    def _decode(self, row: dict[str, Any]) -> dict[str, Any]:
        decoded = dict(row)
        for key in ("tools", "channels", "schedules", "memory", "skills", "interaction_rules", "guardrails", "nodes", "edges", "metadata", "payload"):
            if key in decoded and isinstance(decoded[key], str):
                try:
                    decoded[key] = json.loads(decoded[key])
                except json.JSONDecodeError:
                    pass
        return decoded
