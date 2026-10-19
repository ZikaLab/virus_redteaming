"""Claude API settings read from the environment."""

import os
from dataclasses import dataclass

from virus_redteaming.claude_harness.errors import MissingClaudeApiKeyError

DEFAULT_MODEL = "claude-haiku-5-5"
API_KEY_ENV = "ANTHROPIC_API_KEY"
MODEL_ENV = "ANTHROPIC_MODEL"
WORKSPACE_ENV = "ANTHROPIC_WORKSPACE_ID"


@dataclass(frozen=True)
class ClaudeApiConfig:
    """Model id and API key. The key is omitted from ``repr``."""

    api_key: str
    model: str = DEFAULT_MODEL
    workspace_id: str | None = None

    def __repr__(self) -> str:
        return (
            f"ClaudeApiConfig(model={self.model!r}, workspace_id={self.workspace_id!r})"
        )

    @classmethod
    def from_environment(cls) -> "ClaudeApiConfig":
        """Read the API key, optional model, and optional workspace id."""
        raw_key = os.environ.get(API_KEY_ENV, "").strip()
        if not raw_key:
            raise MissingClaudeApiKeyError(
                f"{API_KEY_ENV} is not set. Add it to .env as {API_KEY_ENV}=..."
            )
        raw_model = os.environ.get(MODEL_ENV, "").strip()
        model = raw_model or DEFAULT_MODEL
        raw_workspace = os.environ.get(WORKSPACE_ENV, "").strip()
        workspace_id = raw_workspace or None
        return cls(api_key=raw_key, model=model, workspace_id=workspace_id)
