from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database_path: Path = ROOT / "yuno_orchestrator.db"
    host: str = os.getenv("YUNO_HOST", "127.0.0.1")
    port: int = int(os.getenv("YUNO_PORT", "8080"))
    llm_provider: str = os.getenv("YUNO_LLM_PROVIDER", "local")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("YUNO_OPENAI_MODEL", "gpt-4.1-mini")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_workflow_id: str = os.getenv("TELEGRAM_WORKFLOW_ID", "workflow-support")
    enable_telegram: bool = os.getenv("ENABLE_TELEGRAM", "false").lower() in {"1", "true", "yes"}


def load_settings() -> Settings:
    return Settings()
