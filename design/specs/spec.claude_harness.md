# spec.claude_harness.md

**Status:** proposed  
**Date:** 2026-10-18  
**ADR:** [0008-claude-langgraph-ping.md](../decisions/0008-claude-langgraph-ping.md)  
**Package:** `src/virus_redteaming/claude_harness/`  
**CLI:** `scripts/claude_ping.py`

## Scope and companion spec

Two specs share `src/virus_redteaming/claude_harness/`:

| Spec file | Scope | Entrypoint | Protocol seam |
| --- | --- | --- | --- |
| `spec.claude_harness.md` (this file, underscore) | Connection ping and 20-chain parallel harness verification | `scripts/claude_ping.py` | `ChatTurn.complete(prompt: str) -> str` |
| [spec.claude-harness.md](spec.claude-harness.md) (hyphen) | Red-team sequence evaluation with Files API upload | `python -m virus_redteaming claude-red-team` | `DocumentTurn.ask(prompt: str, file_id: str) -> str` and `SequenceStore` |

This document specifies the plain-string `ChatTurn` contract, the one-node LangGraph (`build_ping_graph`), the three `HarnessLayer` execution modes, `HaikuBatch`, and `scripts/claude_ping.py`. `spec.claude-harness.md` extends `AnthropicChat` with `DocumentTurn` and adds wave scheduling (`RedTeamBatch`) without changing the `ChatTurn` contract defined here.

## Goal

1. Prove that one LangGraph node can authenticate and complete a prompt against the Claude API using credentials from `.env` (`python scripts/claude_ping.py`, 1 chain on `HarnessLayer.TEST`).
2. Verify 20-chain concurrent execution pinned to `claude-haiku-5-5` with traceable per-chain prompts (`python scripts/claude_ping.py test-batch`, 20 chains on `HarnessLayer.TEST_PARALLEL`).
3. Verify 20-chain concurrent execution using the configured `ANTHROPIC_MODEL` (`python scripts/claude_ping.py live`, 20 chains on `HarnessLayer.LIVE`).

## Constitution

Layout and design follow `constitution/CONSTITUTION.md`:

- Production classes live in `src/virus_redteaming/claude_harness/`. `__init__.py` is a package marker with no logic.
- High-level workflows (`build_ping_graph`, `ClaudePing`, `HaikuBatch`) depend only on Protocols (`ChatTurn`, `ChatTurnFactory`) and never import `AnthropicChat` or `langchain_anthropic`.
- `HaikuBatch` owns the rule that `test-batch` pins the model to `claude-haiku-5-5`; it receives `ClaudeApiConfig` and an injected `ChatTurnFactory`, pins the config with `haiku_batch_config`, and constructs the `ChatTurn` through the factory.
- `scripts/claude_ping.py` is the composition root: it loads `.env`, reads `ClaudeApiConfig`, injects `AnthropicChat`, and formats stdout/stderr. It contains no model-pinning or graph rules.

## Environment

| Variable | Constant | Required | Meaning |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | `API_KEY_ENV` | yes | Claude API key. Stripped; empty or whitespace raises `MissingClaudeApiKeyError`. |
| `ANTHROPIC_MODEL` | `MODEL_ENV` | no | Model id for `TEST` and `LIVE` runs. Stripped; defaults to `DEFAULT_MODEL` (`claude-haiku-5-5`) when unset or blank. Ignored by `HaikuBatch` (`TEST_PARALLEL`), which pins `HAIKU_MODEL` (`claude-haiku-5-5`). |
| `ANTHROPIC_WORKSPACE_ID` | `WORKSPACE_ENV` | when key is not workspace-scoped | Stripped; `None` when unset or blank. When set, sent as the `anthropic-workspace-id` HTTP header (for example `wrkspc_...`). |

`scripts/claude_ping.py` calls `load_dotenv(override=True)` before calling `ClaudeApiConfig.from_environment()`, so values in `.env` replace any placeholder exported in the shell. Library modules in `src/virus_redteaming/claude_harness/` read `os.environ` only and never call `load_dotenv`.

## Types

| Type / Function | Module | Responsibility |
| --- | --- | --- |
| `MissingClaudeApiKeyError` | `errors.py` | Subclass of `VirusRedteamingError`. Raised when `ANTHROPIC_API_KEY` is unset or whitespace. |
| `EmptyClaudeReplyError` | `errors.py` | Subclass of `VirusRedteamingError`. Raised by `ClaudePing.run` when the reply is empty or whitespace. |
| `ChainCountError` | `errors.py` | Subclass of `VirusRedteamingError`. Raised by `ClaudePing.run_layer` before any chain starts when `len(prompts) != layer.chain_count()`. |
| `ClaudeApiConfig` | `config.py` | Frozen dataclass holding `api_key: str`, `model: str = "claude-haiku-5-5"`, and `workspace_id: str | None = None`. `from_environment()` reads the three environment variables above. `__repr__` returns `ClaudeApiConfig(model=..., workspace_id=...)` and omits `api_key`. |
| `ChatTurn` | `protocols.py` | Protocol with `complete(prompt: str) -> str`. |
| `ChatTurnFactory` | `protocols.py` | Protocol `(__call__(config: ClaudeApiConfig) -> ChatTurn)` used to inject client construction into `HaikuBatch` without importing `AnthropicChat`. |
| `AnthropicChat` | `anthropic_chat.py` | Concrete `ChatTurn` backed by `ChatAnthropic`. Wraps `config.api_key` in `SecretStr`, sets `model_name=config.model`, `max_tokens_to_sample=max_tokens` (default `256`), `timeout=timeout` (default `None`), `stop=None`, and `default_headers={"anthropic-workspace-id": config.workspace_id}` when `config.workspace_id` is set. Leaves `effort` unset so the API default applies. `complete(prompt)` invokes the model and flattens string or content-block replies into one string. |
| `PingState`, `PingGraph`, `build_ping_graph` | `graph.py` | `PingState` is a `TypedDict` with `prompt: str` and `reply: str`. `build_ping_graph(chat: ChatTurn) -> PingGraph` builds an uncompiled one-node `StateGraph` (`START -> "claude" -> END`). |
| `HarnessLayer` | `layers.py` | Enum with `TEST = "test"` (1 chain), `TEST_PARALLEL = "test_parallel"` (20 chains), and `LIVE = "live"` (20 chains). `chain_count() -> int` returns the required chain count for the layer. |
| `ClaudePing` | `workflow.py` | Compiles `build_ping_graph(chat)` once in `__init__`. `run(prompt: str) -> str` invokes the compiled graph with a fresh `PingState` and raises `EmptyClaudeReplyError` if `reply.strip()` is empty. `run_layer(layer: HarnessLayer, prompts: Sequence[str]) -> tuple[str, ...]` validates `len(prompts) == layer.chain_count()`, runs `TEST` on the caller thread, and runs `TEST_PARALLEL` and `LIVE` on a `ThreadPoolExecutor(max_workers=20)` preserving prompt order. |
| `HAIKU_MODEL`, `haiku_batch_config`, `haiku_batch_prompts` | `haiku_batch.py` | `HAIKU_MODEL = "claude-haiku-5-5"`. `haiku_batch_config(config)` returns a copy of `config` with `model=HAIKU_MODEL` and the same `api_key` and `workspace_id`. `haiku_batch_prompts()` returns 20 prompts (`"Reply with the single word pong and the number {n}."` for `n` in `1..20`). |
| `HaikuBatch` | `haiku_batch.py` | Takes `(config: ClaudeApiConfig, chat_factory: ChatTurnFactory)` in `__init__`, pins `config` via `haiku_batch_config(config)`, and constructs `ClaudePing(chat_factory(pinned))`. `run() -> tuple[str, ...]` executes `run_layer(HarnessLayer.TEST_PARALLEL, haiku_batch_prompts())`. |

## Layers

`HarnessLayer` defines the concurrency width and the run role. It does **not** select network vs. offline execution: the caller's injected `ChatTurn` determines whether calls reach the Anthropic API (`AnthropicChat`) or stay in memory (a unit-test fake).

| Layer | Enum value | Chains | Execution path in `ClaudePing.run_layer` | Model and prompt policy in CLI | Production callers |
| --- | --- | --- | --- | --- | --- |
| `TEST` | `"test"` | 1 | Caller thread (`(self.run(prompts[0]),)`), no thread pool | `ClaudeApiConfig.model` (`ANTHROPIC_MODEL`, default `claude-haiku-5-5`), 1 pong prompt | `python scripts/claude_ping.py` (no arguments) |
| `TEST_PARALLEL` | `"test_parallel"` | 20 | `ThreadPoolExecutor(max_workers=20)`, `pool.map(self.run, prompts)` | Pinned to `claude-haiku-5-5` via `haiku_batch_config` (ignores `ANTHROPIC_MODEL`), 20 numbered prompts (`1..20`) | `python scripts/claude_ping.py test-batch` (`HaikuBatch.run`) |
| `LIVE` | `"live"` | 20 | `ThreadPoolExecutor(max_workers=20)`, `pool.map(self.run, prompts)` | `ClaudeApiConfig.model` (`ANTHROPIC_MODEL`, default `claude-haiku-5-5`), 20 concurrent prompts | `python scripts/claude_ping.py live`, and wave width (`HarnessLayer.LIVE.chain_count()`) in `spec.claude-harness.md` |

Rules across all layers:

1. `run_layer` checks `len(prompts) == layer.chain_count()` before starting any chain. A mismatch raises `ChainCountError` with `"{layer.value} runs {expected} chain(s), received {len(prompts)} prompts"`.
2. Chains in `TEST_PARALLEL` and `LIVE` share one compiled LangGraph and one `ChatTurn` instance. Each `invoke` receives a fresh `{"prompt": prompt, "reply": ""}` dictionary so state never leaks across threads.
3. `pool.map` returns replies in input prompt order regardless of completion order. The first chain exception propagates to the caller after active worker threads exit.

## CLI (`scripts/claude_ping.py`)

```bash
python scripts/claude_ping.py
python scripts/claude_ping.py test-batch
python scripts/claude_ping.py live
```

| Invocation (`argv`) | Layer | Chains | Model | Prompts |
| --- | --- | --- | --- | --- |
| `[]` (no arguments) | `HarnessLayer.TEST` | 1 | `config.model` | `("Reply with the single word pong.",)` |
| `["test-batch"]` | `HarnessLayer.TEST_PARALLEL` (via `HaikuBatch(config, AnthropicChat)`) | 20 | `claude-haiku-5-5` (pinned by `HaikuBatch`) | `haiku_batch_prompts()` (`pong` + `1..20`) |
| `["live"]` | `HarnessLayer.LIVE` | 20 | `config.model` | `("Reply with the single word pong.",) * 20` |
| Any other arguments | none | 0 | none | Prints `usage: python scripts/claude_ping.py [test-batch|live]` to `stderr` and exits `2` before reading `.env`. |

### Output and exit codes

| Exit code | Condition | Output |
| --- | --- | --- |
| `0` | All chains in the selected layer returned non-empty replies | Prints `{index}. {reply}` (1-based) to `stdout` in prompt order (1 line for no arguments, 20 lines for `test-batch` and `live`). |
| `2` | Unrecognized CLI arguments, or `MissingClaudeApiKeyError` from `ClaudeApiConfig.from_environment()` | Prints the usage line or error message to `stderr`. |
| `1` | Any exception raised while constructing the client or running the layer (`EmptyClaudeReplyError`, HTTP/authentication error, etc.) | Redacts every match of `sk-ant-[A-Za-z0-9_\-]+` to `***` and prints the redacted text to `stderr`. If the redacted message contains `"anthropic-workspace-id"`, also prints `"Set ANTHROPIC_WORKSPACE_ID in .env to a wrkspc_ id from the Claude Console workspaces page."` to `stderr`. |

## Tests

Unit tests live in `tests/unit/claude_harness/test_ping.py`. They inject fake `ChatTurn` and `ChatTurnFactory` implementations and never open a network connection.

| Test | Asserts |
| --- | --- |
| `test_missing_key_names_the_variable` | Unset `ANTHROPIC_API_KEY` raises `MissingClaudeApiKeyError` naming `ANTHROPIC_API_KEY`. |
| `test_blank_key_is_missing` | Whitespace-only `ANTHROPIC_API_KEY` raises `MissingClaudeApiKeyError`. |
| `test_repr_omits_the_key` | `repr(config)` includes `model` and `workspace_id` and omits `api_key`. |
| `test_workspace_id_is_optional` | Unset `ANTHROPIC_WORKSPACE_ID` sets `config.workspace_id` to `None`. |
| `test_workspace_id_is_read` | Padded `ANTHROPIC_WORKSPACE_ID` is stripped and stored on `config.workspace_id`. |
| `test_default_model_when_unset` | Unset `ANTHROPIC_MODEL` defaults `config.model` to `"claude-haiku-5-5"`. |
| `test_graph_returns_the_fake_reply` | `ClaudePing(fake).run(prompt)` passes `prompt` to `fake.complete` and returns its reply. |
| `test_empty_reply_is_an_error` | Whitespace-only reply from `ChatTurn.complete` raises `EmptyClaudeReplyError`. |
| `test_test_layer_runs_one_chain` | `ClaudePing(fake).run_layer(HarnessLayer.TEST, ("only",))` runs 1 chain and returns `("pong",)`. |
| `test_test_layer_rejects_twenty_prompts` | Passing 20 prompts to `HarnessLayer.TEST` raises `ChainCountError` matching `"test runs 1 chain"` without calling `complete`. |
| `test_parallel_layer_runs_twenty_chains` | `HarnessLayer.TEST_PARALLEL` releases 20 chains concurrently across a `threading.Barrier(20)` and returns replies in prompt order. |
| `test_parallel_layer_rejects_one_prompt` | Passing 1 prompt to `HarnessLayer.TEST_PARALLEL` raises `ChainCountError` matching `"test_parallel runs 20 chains"`. |
| `test_live_layer_runs_twenty_chains_on_the_injected_client` | `HarnessLayer.LIVE` releases 20 chains concurrently across a `threading.Barrier(20)` on a fake client and returns replies in prompt order. |
| `test_live_layer_rejects_one_prompt` | Passing 1 prompt to `HarnessLayer.LIVE` raises `ChainCountError` matching `"live runs 20 chains"`. |
| `test_haiku_batch_pins_model_and_builds_twenty_prompts` | `haiku_batch_config` overrides `model="claude-opus-5-5"` to `"claude-haiku-5-5"` while keeping `api_key` and `workspace_id`; `haiku_batch_prompts()` returns 20 numbered prompts ending `"1."` through `"20."`. |
| `test_haiku_batch_runs_twenty_prompts_with_pinned_config` | `HaikuBatch(config, fake_factory).run()` passes the Haiku-pinned `ClaudeApiConfig` into `fake_factory` and sends `haiku_batch_prompts()` through `HarnessLayer.TEST_PARALLEL` without importing or calling `AnthropicChat`. |
| `test_cli_no_args_runs_test_layer_single_chain` | `main([])` runs `HarnessLayer.TEST` (1 chain), prints `1. pong`, and returns `0`. |
| `test_cli_test_batch_runs_haiku_batch` | `main(["test-batch"])` runs `HaikuBatch`, prints 20 numbered lines (`1. ...` through `20. ...`), and returns `0`. |
| `test_cli_live_runs_twenty_chains_with_configured_model` | `main(["live"])` runs `HarnessLayer.LIVE` (20 chains) with `config.model`, prints 20 numbered lines, and returns `0`. |
| `test_cli_unknown_argument_exits_2` | `main(["unknown"])` prints usage to `stderr` and returns `2` without calling Claude. |
| `test_cli_missing_key_exits_2` | `main([])` with missing `ANTHROPIC_API_KEY` prints the missing-key message to `stderr` and returns `2`. |
| `test_cli_client_error_redacts_key_and_prints_workspace_hint` | When the client raises an error containing an `sk-ant-...` token and `"anthropic-workspace-id"`, `main([])` redacts the token to `***`, prints the workspace hint to `stderr`, and returns `1`. |
