from __future__ import annotations

from typing import Any


AGENTS: list[dict[str, Any]] = [
    {
        "id": "agent-triage",
        "name": "Triage Agent",
        "role": "Customer support triage",
        "system_prompt": "Classify customer requests, collect context with tools, and route to the correct next agent.",
        "model": "local-reasoner",
        "tools": ["order_lookup", "policy_lookup"],
        "channels": ["telegram", "web"],
        "schedules": [{"type": "business-hours", "timezone": "Asia/Kolkata"}],
        "memory": {"tone": "calm, concise, transparent"},
        "skills": ["classification", "routing", "customer-context-gathering"],
        "interaction_rules": ["Do not promise refunds without policy and order context."],
        "guardrails": ["Ask for an order id before sharing account-specific details."],
    },
    {
        "id": "agent-resolution",
        "name": "Resolution Agent",
        "role": "Customer support resolution specialist",
        "system_prompt": "Resolve eligible customer issues, calculate refunds, create tickets, and produce a customer-safe response.",
        "model": "local-reasoner",
        "tools": ["order_lookup", "refund_calculator", "ticket_creator", "policy_lookup"],
        "channels": ["web"],
        "schedules": [],
        "memory": {"refund_limit_inr": 3000},
        "skills": ["refunds", "ticketing", "customer-replies"],
        "interaction_rules": ["Escalate high-risk or high-value cases."],
        "guardrails": ["Never reveal internal policy verbatim to customers."],
    },
    {
        "id": "agent-research",
        "name": "Research Agent",
        "role": "Research scout",
        "system_prompt": "Collect structured notes for a requested topic and pass them to a reviewer.",
        "model": "local-reasoner",
        "tools": ["research_notes"],
        "channels": ["web"],
        "schedules": [{"type": "daily", "time": "09:00"}],
        "memory": {"format": "bulleted evidence notes"},
        "skills": ["research", "synthesis"],
        "interaction_rules": ["Separate facts, assumptions, and recommendations."],
        "guardrails": ["Flag unknowns instead of inventing citations."],
    },
    {
        "id": "agent-critic",
        "name": "Critic Agent",
        "role": "Review critic",
        "system_prompt": "Review intermediate work for gaps, risks, and next actions.",
        "model": "local-reasoner",
        "tools": ["critique_brief"],
        "channels": ["web"],
        "schedules": [],
        "memory": {"max_revision_loops": 1},
        "skills": ["quality-review", "risk-analysis"],
        "interaction_rules": ["Approve only when the answer is actionable."],
        "guardrails": ["Keep critique constructive and brief."],
    },
    {
        "id": "agent-writer",
        "name": "Writer Agent",
        "role": "Executive writer",
        "system_prompt": "Turn reviewed research into an executive-ready brief.",
        "model": "local-reasoner",
        "tools": ["research_notes"],
        "channels": ["web"],
        "schedules": [],
        "memory": {"voice": "clear, practical, founder-friendly"},
        "skills": ["writing", "summarization"],
        "interaction_rules": ["Prefer crisp recommendations over generic summaries."],
        "guardrails": ["Do not cite sources that were not provided by the research step."],
    },
]


WORKFLOWS: list[dict[str, Any]] = [
    {
        "id": "workflow-support",
        "name": "Customer Support Swarm",
        "description": "Telegram-ready workflow where triage and resolution agents collaborate on an order issue.",
        "template_key": "support-swarm",
        "nodes": [
            {"id": "node-triage", "agent_id": "agent-triage", "x": 80, "y": 92},
            {"id": "node-resolution", "agent_id": "agent-resolution", "x": 390, "y": 92},
        ],
        "edges": [
            {"from": "node-triage", "to": "node-resolution", "condition": "resolve", "label": "has order context"},
            {"from": "node-resolution", "to": "node-triage", "condition": "needs_followup", "label": "feedback loop"},
        ],
    },
    {
        "id": "workflow-research",
        "name": "Research Brief Factory",
        "description": "Researcher, critic, and writer agents produce a reviewed brief with a visible feedback loop.",
        "template_key": "research-brief",
        "nodes": [
            {"id": "node-research", "agent_id": "agent-research", "x": 50, "y": 105},
            {"id": "node-critic", "agent_id": "agent-critic", "x": 330, "y": 40},
            {"id": "node-writer", "agent_id": "agent-writer", "x": 610, "y": 105},
        ],
        "edges": [
            {"from": "node-research", "to": "node-critic", "condition": "review", "label": "review"},
            {"from": "node-critic", "to": "node-research", "condition": "revise", "label": "feedback loop"},
            {"from": "node-critic", "to": "node-writer", "condition": "approve", "label": "approved"},
        ],
    },
]


TEMPLATES = [
    {
        "key": "support-swarm",
        "name": "Customer Support Swarm",
        "description": "2-agent order support flow with Telegram ingress, tools, routing, and customer-safe response.",
    },
    {
        "key": "research-brief",
        "name": "Research Brief Factory",
        "description": "3-agent research/review/write flow with a critic feedback loop.",
    },
]


def seed_demo_data(store: Any) -> None:
    for agent in AGENTS:
        store.upsert_agent(agent)
    for workflow in WORKFLOWS:
        store.upsert_workflow(workflow)
