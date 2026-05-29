from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import Settings


class Reasoner:
    def generate(self, agent: dict[str, Any], user_input: str, tool_results: list[dict[str, Any]], memory: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class LocalReasoner(Reasoner):
    """Deterministic local model for reliable demos without API keys."""

    def generate(self, agent: dict[str, Any], user_input: str, tool_results: list[dict[str, Any]], memory: dict[str, Any]) -> dict[str, Any]:
        role = agent["role"].lower()
        tools = {item["name"]: item["output"] for item in tool_results}
        text = user_input.lower()
        route = "default"

        if "triage" in role:
            order = tools.get("order_lookup", {})
            policy = tools.get("policy_lookup", {})
            route = "resolve" if order.get("status") != "unknown" else "ask_for_order"
            content = (
                f"I found {order.get('order_id')} for {order.get('customer', 'the customer')}. "
                f"Status is {order.get('status')} because of {order.get('reason')}. "
                f"Routing to the resolution specialist with policy context: {self._short(policy)}"
            )
        elif "resolution" in role:
            order = tools.get("order_lookup", {})
            refund = tools.get("refund_calculator", {})
            ticket = tools.get("ticket_creator", {})
            route = "complete"
            coupon = " Add a 10% goodwill coupon because the delay is material." if order.get("status") == "delayed" else ""
            approval = "Refund approved" if refund.get("approved") else "Refund needs human approval"
            content = (
                f"Customer reply: Sorry for the inconvenience. Your order {order.get('order_id')} is "
                f"{order.get('status')} with ETA {order.get('eta')}. {approval} up to INR {refund.get('amount_inr')}. "
                f"Reference ticket {ticket.get('ticket_id')}.{coupon}"
            )
        elif "critic" in role or "review" in role:
            critique = tools.get("critique_brief", {})
            route = "revise" if "unclear" in text else "approve"
            content = f"Review verdict: {critique.get('verdict', 'approved')}. Risks: {', '.join(critique.get('risks', []))}"
        elif "writer" in role:
            notes = tools.get("research_notes", {})
            findings = notes.get("findings", [])
            content = "Executive brief:\n" + "\n".join(f"- {item}" for item in findings)
            route = "complete"
        else:
            notes = tools.get("research_notes", {})
            content = f"Research packet for {notes.get('topic', user_input)}: {self._short(notes)}"
            route = "review"

        tokens = max(30, len((user_input + content).split()) * 2)
        return {"content": content, "route": route, "token_count": tokens, "cost_cents": round(tokens * 0.00002, 4)}

    def _short(self, value: Any) -> str:
        rendered = json.dumps(value, ensure_ascii=True)
        return rendered[:180] + ("..." if len(rendered) > 180 else "")


class OpenAIReasoner(Reasoner):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.fallback = LocalReasoner()

    def generate(self, agent: dict[str, Any], user_input: str, tool_results: list[dict[str, Any]], memory: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            return self.fallback.generate(agent, user_input, tool_results, memory)
        payload = {
            "model": agent.get("model") or self.settings.openai_model,
            "input": [
                {"role": "system", "content": agent["system_prompt"]},
                {
                    "role": "user",
                    "content": (
                        "Return a concise operational response. Include route as one of "
                        "resolve, complete, review, approve, revise, ask_for_order.\n"
                        f"User input: {user_input}\nTool results: {json.dumps(tool_results)}\nMemory: {json.dumps(memory)}"
                    ),
                },
            ],
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                data = json.loads(res.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return self.fallback.generate(agent, user_input, tool_results, memory)
        content = data.get("output_text") or self._extract_output(data) or "No model output returned."
        tokens = data.get("usage", {}).get("total_tokens", max(30, len(content.split()) * 2))
        return {"content": content, "route": self._infer_route(content), "token_count": tokens, "cost_cents": round(tokens * 0.00015, 4)}

    def _extract_output(self, data: dict[str, Any]) -> str:
        chunks: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text", ""))
        return "\n".join(chunk for chunk in chunks if chunk)

    def _infer_route(self, content: str) -> str:
        lowered = content.lower()
        for route in ("resolve", "complete", "review", "approve", "revise", "ask_for_order"):
            if route in lowered:
                return route
        return "default"


def build_reasoner(settings: Settings) -> Reasoner:
    return OpenAIReasoner(settings) if settings.llm_provider == "openai" else LocalReasoner()
