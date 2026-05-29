from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolResult:
    name: str
    output: dict[str, Any]


ORDERS = {
    "ORD-1024": {
        "customer": "Aarav Mehta",
        "status": "delayed",
        "eta": "2026-05-27",
        "value": 2499,
        "risk": "low",
        "reason": "courier hub backlog",
    },
    "ORD-2048": {
        "customer": "Priya Shah",
        "status": "delivered",
        "eta": "2026-05-21",
        "value": 1299,
        "risk": "medium",
        "reason": "delivered with packaging complaint",
    },
}


KNOWLEDGE_BASE = {
    "refund": "Refunds below INR 3000 can be approved by a resolution agent when fraud risk is low or medium.",
    "delay": "Delayed shipments should receive an apology, updated ETA, and a goodwill coupon when the delay is over 48 hours.",
    "escalation": "Escalate to a human when the customer is angry, legal language appears, or order value exceeds INR 5000.",
}


def extract_order_id(text: str) -> str:
    match = re.search(r"ORD-\d{4,}", text.upper())
    return match.group(0) if match else "ORD-1024"


def order_lookup(text: str) -> ToolResult:
    order_id = extract_order_id(text)
    order = ORDERS.get(order_id, {"status": "unknown", "eta": "unknown", "value": 0, "risk": "unknown", "reason": "not found"})
    return ToolResult("order_lookup", {"order_id": order_id, **order})


def policy_lookup(text: str) -> ToolResult:
    hits = {key: value for key, value in KNOWLEDGE_BASE.items() if key in text.lower()}
    if not hits:
        hits = {"general": "Be concise, transparent, and ask for missing identifiers before taking account actions."}
    return ToolResult("policy_lookup", hits)


def refund_calculator(text: str, order: dict[str, Any] | None = None) -> ToolResult:
    value = int((order or {}).get("value", 1499))
    risk = (order or {}).get("risk", "medium")
    amount = min(value, 3000)
    approved = risk in {"low", "medium"} and amount <= 3000
    return ToolResult("refund_calculator", {"approved": approved, "amount_inr": amount, "risk": risk})


def ticket_creator(text: str) -> ToolResult:
    severity = "high" if any(word in text.lower() for word in ["angry", "legal", "lawsuit", "urgent"]) else "normal"
    return ToolResult("ticket_creator", {"ticket_id": f"YUNO-{abs(hash(text)) % 90000 + 10000}", "severity": severity})


def research_notes(text: str) -> ToolResult:
    topic = text.strip().rstrip(".") or "agent orchestration"
    return ToolResult(
        "research_notes",
        {
            "topic": topic,
            "findings": [
                f"{topic} benefits from explicit agent contracts and persisted event logs.",
                "Human handoff should be modeled as a first-class channel, not an exception path.",
                "Feedback loops need max-step limits and visible traceability for operations teams.",
            ],
        },
    )


def critique_brief(text: str) -> ToolResult:
    return ToolResult(
        "critique_brief",
        {
            "risks": [
                "Confirm assumptions before external customer messaging.",
                "Keep cost and token telemetry attached to every run.",
            ],
            "verdict": "ready_with_minor_edits",
        },
    )


ToolFn = Callable[..., ToolResult]


TOOLS: dict[str, ToolFn] = {
    "order_lookup": order_lookup,
    "policy_lookup": policy_lookup,
    "refund_calculator": refund_calculator,
    "ticket_creator": ticket_creator,
    "research_notes": research_notes,
    "critique_brief": critique_brief,
}
