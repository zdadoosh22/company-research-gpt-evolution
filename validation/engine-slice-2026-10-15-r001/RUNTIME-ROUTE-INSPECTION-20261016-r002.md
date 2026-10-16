# `exec-server` route inspection — 16 October 2026 (r002)

## Finding

The installed `codex exec-server` interface does not expose a tool-inventory or tool-preparation discovery route. Its documented purpose is to run a standalone execution server; the only subcommand is `forward`, which registers an existing WebSocket exec-server as a remote environment. No exec-server protocol-schema generator is documented in its help. This lead does not provide a route for observing the complete tools registered to a `codex exec` model turn and does not change the runtime gate.

## Inspected interface

Installed CLI: `codex-cli 0.162.0-alpha.17.2` (same binary as recorded in `RUNTIME-ROUTE-INSPECTION-20261016.md`). Help-only commands:

- `codex exec-server --help`
- `codex exec-server help`
- `codex exec-server forward --help`

The top-level help documents listening transports (`ws://IP:PORT`, `stdio`, `stdio://`), concurrency, authentication modes and token/secret options, Linux PID namespace, proxy routing, and optional remote registration. The `forward` help requires `--remote`, `--environment-id`, and `--connect` and describes registering the environment. No service was started and no forwarding/registration command was run.

## Boundary

This was CLI help inspection only. No inference, daemon request, account/credential access, or tool call occurred. The parent-reported Windows canary establishes its synthetic file allow/deny result only; `exec-server` help supplies no evidence about hosted model tools or complete `codex exec` tool removal. Keep the existing fail-closed worker restriction until evidence covers the exact worker route and relevant capabilities.
