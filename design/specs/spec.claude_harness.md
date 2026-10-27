# Claude LangGraph connection ping

Status: accepted
Date: 2026-10-18
ADR: [0008-claude-langgraph-ping.md](../decisions/0008-claude-langgraph-ping.md)

## Goal

Prove that a LangGraph node can call Claude with the key in `.env`.

## Environment

| Variable | Required | Meaning |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | yes | Claude API key. Empty or whitespace is a missing key. |
| `ANTHROPIC_MODEL` | no | Model id. Default `claude-haiku-5-5`. |
| `ANTHROPIC_WORKSPACE_ID` | when the key is not scoped to one workspace | Sent as the `anthropic-workspace-id` header. Example shape: `wrkspc_...`. |

`scripts/claude_ping.py` calls `load_dotenv(override=True)` before reading the environment, so `.env` replaces a placeholder already exported in the shell. The library reads `os.environ` only.

## Types

| Type | Module | Job |
| --- | --- | --- |
| `ClaudeApiConfig` | `config.py` | Holds the model id, key, and optional workspace id. `from_environment` reads the variables above. `repr` omits the key. |
| `ChatTurn` | `protocols.py` | `complete(prompt) -> str`. |
| `AnthropicChat` | `anthropic_chat.py` | `ChatTurn` over `ChatAnthropic`. Flattens text blocks. |
| `HarnessLayer` | `layers.py` | `TEST` is 1 chain. `TEST_PARALLEL` and `LIVE` are 20 chains. |
| `PingState`, `build_ping_graph` | `graph.py` | One node. Each invoke has its own prompt and reply. |
| `MissingClaudeApiKeyError`, `EmptyClaudeReplyError`, `ChainCountError` | `errors.py` | Missing key, empty reply, or a prompt list whose length is not the layer width. |
| `ClaudePing` | `workflow.py` | One-node graph. `run` is one chain. `run_layer` runs the layer's chains together. |
| `HaikuBatch` | `haiku_batch.py` | Live twenty-chain batch. Pins the model to `claude-haiku-5-5` and uses `TEST_PARALLEL`'s width. |

## Command

```bash
python scripts/claude_ping.py
python scripts/claude_ping.py test-batch
```

No arguments selects `HarnessLayer.LIVE`: 20 chains in one thread pool, each with `Reply with the single word pong.` `test-batch` selects `HaikuBatch`, which uses the same pool width under `HarnessLayer.TEST_PARALLEL` and pins the model to `claude-haiku-5-5`. Chain `n` is asked for `pong` and the number `n`. Any other argument prints usage and exits `2`.

Exit `0` prints the twenty replies, numbered from 1, in prompt order. Exit `2` means the key is missing or the arguments are not recognized. A client or HTTP failure exits `1`. Error text redacts any `sk-ant-` token. The script is the composition root: it constructs `AnthropicChat` for `LIVE` and passes `ClaudeApiConfig` to `HaikuBatch`. The library workflow takes an injected `ChatTurn`.

## Layers

| Layer | Chains | Client | Where it runs |
| --- | --- | --- | --- |
| `TEST` | 1 | Fake `ChatTurn` | Caller thread. No network. |
| `TEST_PARALLEL` | 20 | Fake in unit tests. `HaikuBatch` uses `AnthropicChat` pinned to `claude-haiku-5-5`. | Thread pool of 20. |
| `LIVE` | 20 | `AnthropicChat` | Thread pool of 20. Claude API. |

`run_layer` rejects a prompt list whose length is not the layer's chain count. Replies stay in prompt order. The chains share one compiled graph and one client. Each invoke has its own state.

## Tests

Unit tests in `tests/unit/claude_harness/test_ping.py` inject a fake `ChatTurn` and do not call the network. A missing key, a blank key, a hidden key in `repr`, an optional workspace id, a default model when unset, a returned reply, and an empty reply are the single-chain cases. `TEST` accepts one prompt and rejects twenty. `TEST_PARALLEL` and `LIVE` each accept twenty prompts, release them together on a barrier, and reject one prompt. Those two unit cases inject a fake, so the parallel count is checked without the API. `haiku_batch_config` pins `claude-haiku-5-5` and keeps the key and workspace id. `haiku_batch_prompts` returns twenty numbered prompts. The script is what binds `LIVE` and `test-batch` to Claude.
