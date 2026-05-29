from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from yuno_orchestrator.llm import LocalReasoner
from yuno_orchestrator.runtime import AgentRuntime, EventHub
from yuno_orchestrator.storage import Store
from yuno_orchestrator.templates import seed_demo_data


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.db")
        seed_demo_data(self.store)
        self.hub = EventHub()
        self.runtime = AgentRuntime(self.store, LocalReasoner(), self.hub)

    def tearDown(self) -> None:
        self.runtime.stop()
        self.store.close()
        self.tmp.cleanup()

    def wait_for_run(self, run_id: str) -> dict:
        for _ in range(50):
            run = self.store.get_run(run_id)
            if run and run["status"] in {"completed", "failed"}:
                return run
            time.sleep(0.1)
        self.fail("run did not finish")

    def test_agent_creation_persists_config(self) -> None:
        agent = self.store.upsert_agent(
            {
                "name": "Verifier",
                "role": "Test agent",
                "system_prompt": "Verify things.",
                "model": "local-reasoner",
                "tools": ["policy_lookup"],
                "channels": ["web"],
                "schedules": [{"type": "daily"}],
                "memory": {"foo": "bar"},
                "skills": ["checks"],
                "interaction_rules": ["be direct"],
                "guardrails": ["no secrets"],
            }
        )
        loaded = self.store.get_agent(agent["id"])
        self.assertEqual(loaded["tools"], ["policy_lookup"])
        self.assertEqual(loaded["memory"]["foo"], "bar")

    def test_support_workflow_executes_two_agents(self) -> None:
        result = self.runtime.submit("workflow-support", "My order ORD-1024 is delayed and I want a refund.")
        run = self.wait_for_run(result.run_id)
        self.assertEqual(run["status"], "completed")
        self.assertIn("Customer reply", run["output"])
        self.assertGreater(run["token_count"], 0)

    def test_message_delivery_is_persisted(self) -> None:
        result = self.runtime.submit("workflow-support", "Please check ORD-2048", channel="telegram-simulator")
        self.wait_for_run(result.run_id)
        messages = self.store.list_messages()
        channels = {message["channel"] for message in messages}
        self.assertIn("telegram-simulator", channels)
        self.assertIn("internal", channels)


if __name__ == "__main__":
    unittest.main()
