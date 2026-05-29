# Interview Prep Notes

Use these points for Round 1 when the CTO asks you to explain the submission.

## One-Minute Summary

I built a local-first AI agent orchestration platform. It lets a user configure agents, connect them into workflows, run real tools, persist message history, and monitor execution in real time. The runtime is custom and asynchronous, with SQLite persistence and Telegram integration for external human interaction.

## Why Custom Runtime

The assessment allowed a custom runtime. I chose it because Round 0 rewards a working end-to-end demo, and a small custom runtime is easier to audit and explain than a large framework wrapper. The runtime still has the important production boundaries:

- agent configuration
- tool registry
- async workflow execution
- conditional routing
- feedback-loop protection
- persisted messages
- channel callbacks
- monitoring events

If needed, the `Reasoner` and runtime interfaces can be swapped for LangGraph, CrewAI, AutoGen, or OpenAI-backed model calls.

## Architecture Explanation

The web UI talks to a Python HTTP API. The API stores agents and workflows in SQLite. When a workflow runs, the async runtime executes each agent, calls configured tools, persists messages, emits events, and routes to the next node based on the agent output. Telegram works as an ingress channel and uses a callback to send the final response back to the user.

## Tradeoffs

Good tradeoffs:

- Very easy to run locally
- No Docker or dependency failure risk
- Deterministic local demo
- Clear separation between UI, runtime, tools, channels, and persistence

Known limitations:

- UI is intentionally lightweight
- Local reasoner is deterministic, not a full LLM
- Telegram uses polling, not webhooks, for local demo simplicity
- SQLite is ideal for local demo, but Postgres would be better for multi-user production deployment

## How I Would Productionize It

- Add authentication and user workspaces
- Move runtime workers to separate processes
- Use Postgres for shared persistence
- Add Redis or durable queues for distributed execution
- Add webhook-based channel integrations
- Add LangGraph or OpenAI Assistants for richer model reasoning
- Add RBAC, audit logs, rate limits, and encrypted secrets
- Deploy backend and frontend behind HTTPS

## Best Demo Input

```text
My order ORD-1024 is delayed and I want a refund.
```

This triggers:

- Triage Agent
- order lookup tool
- policy lookup tool
- Resolution Agent
- refund calculation tool
- ticket creation tool
- final customer-safe response

