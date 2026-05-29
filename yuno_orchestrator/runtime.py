from __future__ import annotations

import asyncio
import json
import queue
import threading
from dataclasses import dataclass
from typing import Any

from .llm import Reasoner
from .storage import Store, now_iso
from .tools import TOOLS, ToolResult


class EventHub:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []
        self._lock = threading.RLock()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass


@dataclass
class RuntimeResult:
    run_id: str
    status: str


class AgentRuntime:
    def __init__(self, store: Store, reasoner: Reasoner, hub: EventHub):
        self.store = store
        self.reasoner = reasoner
        self.hub = hub
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        ready = threading.Event()

        def runner() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            ready.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=runner, daemon=True, name="agent-runtime")
        self._thread.start()
        ready.wait(timeout=5)

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def submit(self, workflow_id: str, user_input: str, channel: str = "web", external_reply: Any | None = None) -> RuntimeResult:
        self.start()
        run = self.store.create_run(workflow_id, user_input)
        self._emit(run["id"], "run.queued", f"Workflow {workflow_id} queued", {"workflow_id": workflow_id, "channel": channel})
        assert self._loop is not None
        asyncio.run_coroutine_threadsafe(self._run_workflow(run["id"], workflow_id, user_input, channel, external_reply), self._loop)
        return RuntimeResult(run_id=run["id"], status="queued")

    async def _run_workflow(self, run_id: str, workflow_id: str, user_input: str, channel: str, external_reply: Any | None) -> None:
        workflow = self.store.get_workflow(workflow_id)
        if not workflow:
            self.store.update_run(run_id, status="failed", output=f"Workflow {workflow_id} not found", ended_at=now_iso())
            return

        self.store.update_run(run_id, status="running")
        nodes = workflow["nodes"]
        edges = workflow["edges"]
        node_by_id = {node["id"]: node for node in nodes}
        current = nodes[0] if nodes else None
        context = user_input
        total_tokens = 0
        total_cost = 0.0
        steps = 0
        max_steps = 8

        self.store.add_message(
            {
                "run_id": run_id,
                "workflow_id": workflow_id,
                "sender": channel,
                "recipient": current["id"] if current else "workflow",
                "channel": channel,
                "content": user_input,
                "metadata": {"ingress": True},
            }
        )

        final_output = ""
        while current and steps < max_steps:
            steps += 1
            agent = self.store.get_agent(current["agent_id"])
            if not agent:
                final_output = f"Missing agent {current['agent_id']}"
                break
            self._emit(run_id, "agent.started", f"{agent['name']} started", {"agent_id": agent["id"], "step": steps})
            await asyncio.sleep(0.15)
            result = await self._execute_agent(agent, context)
            total_tokens += int(result.get("token_count", 0))
            total_cost += float(result.get("cost_cents", 0))
            final_output = result["content"]
            self.store.add_message(
                {
                    "run_id": run_id,
                    "workflow_id": workflow_id,
                    "agent_id": agent["id"],
                    "sender": agent["name"],
                    "recipient": "workflow",
                    "channel": "internal",
                    "content": final_output,
                    "metadata": {"route": result.get("route"), "tool_results": result.get("tool_results", [])},
                }
            )
            self._emit(
                run_id,
                "agent.completed",
                f"{agent['name']} completed with route {result.get('route')}",
                {"agent_id": agent["id"], "route": result.get("route"), "tokens": result.get("token_count", 0)},
            )
            next_node = self._next_node(current["id"], result.get("route", "default"), edges, node_by_id)
            context = f"{context}\n\n{agent['name']} said:\n{final_output}"
            current = next_node

        if steps >= max_steps:
            final_output = f"{final_output}\n\nStopped after {max_steps} steps to prevent an infinite feedback loop."

        self.store.update_run(run_id, status="completed", output=final_output, token_count=total_tokens, cost_cents=round(total_cost, 4), ended_at=now_iso())
        self._emit(run_id, "run.completed", "Workflow completed", {"output": final_output, "tokens": total_tokens, "cost_cents": round(total_cost, 4)})
        if external_reply:
            try:
                external_reply(final_output)
            except Exception as exc:  # noqa: BLE001 - channel callbacks must not crash runtime
                self._emit(run_id, "channel.error", f"External reply failed: {exc}", {})

    async def _execute_agent(self, agent: dict[str, Any], context: str) -> dict[str, Any]:
        tool_results: list[ToolResult] = []
        order_context: dict[str, Any] | None = None
        for tool_name in agent.get("tools", []):
            tool = TOOLS.get(tool_name)
            if not tool:
                continue
            if tool_name == "refund_calculator":
                result = tool(context, order_context)
            else:
                result = tool(context)
            if tool_name == "order_lookup":
                order_context = result.output
            tool_results.append(result)
            await asyncio.sleep(0.05)
        serializable_tools = [{"name": item.name, "output": item.output} for item in tool_results]
        response = self.reasoner.generate(agent, context, serializable_tools, agent.get("memory", {}))
        response["tool_results"] = serializable_tools
        return response

    def _next_node(self, current_id: str, route: str, edges: list[dict[str, Any]], node_by_id: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        outgoing = [edge for edge in edges if edge["from"] == current_id]
        exact = next((edge for edge in outgoing if edge.get("condition") == route), None)
        fallback = next((edge for edge in outgoing if edge.get("condition") in {"default", ""}), None)
        edge = exact or fallback
        return node_by_id.get(edge["to"]) if edge else None

    def _emit(self, run_id: str | None, event_type: str, message: str, payload: dict[str, Any]) -> None:
        event = self.store.add_event(run_id, event_type, message, payload)
        self.hub.publish(event)


def event_to_sse(event: dict[str, Any]) -> bytes:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n".encode("utf-8")
