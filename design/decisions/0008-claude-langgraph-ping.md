# 0008. Claude LangGraph ping

Date: 2026-10-18
Status: accepted

## Context

The harness needs a checked path from this repo to the Claude API before any evaluation graph is built. The Anthropic SDK and LangChain both read `ANTHROPIC_API_KEY`. A one-node LangGraph is enough to prove the client, the key, and the graph runtime work together.

## Decision

Put the ping in `src/virus_redteaming/claude_harness/`. `ClaudeApiConfig` reads `ANTHROPIC_API_KEY`, the optional `ANTHROPIC_MODEL`, and the optional `ANTHROPIC_WORKSPACE_ID`. A key that is not scoped to one workspace needs that id as the `anthropic-workspace-id` header. A `ChatTurn` Protocol hides the Anthropic client. `ClaudePing` runs one LangGraph node and returns the reply text. `scripts/claude_ping.py` only loads dotenv and assembles those objects.

The default model is `claude-haiku-5-5`.

The layer defines the chain count and execution role, while the injected `ChatTurn` determines whether calls reach the API or stay on a unit-test fake:

- `TEST` (1 chain, caller thread): default single-chain connection check (`python scripts/claude_ping.py`).
- `TEST_PARALLEL` (20 chains, thread pool): parallel test batch (`python scripts/claude_ping.py test-batch`) via `HaikuBatch(config, chat_factory)`, which pins the model to `claude-haiku-5-5` regardless of `ANTHROPIC_MODEL` and sends twenty numbered prompts.
- `LIVE` (20 chains, thread pool): full-width live run using `ClaudeApiConfig.model` (`python scripts/claude_ping.py live`) and the wave width read by `RedTeamBatch` in `spec.claude-harness.md`.

A prompt list of any other length is rejected with `ChainCountError` before a chain starts. `scripts/claude_ping.py` is the composition root and the only place these commands reference `AnthropicChat`.

## Consequences

Later graphs depend on `ChatTurn` and inject their own nodes. The API key stays out of `repr`, logs, and exception text. Installing the clients is the optional `harness` extra, so the rest of the package does not require them.
