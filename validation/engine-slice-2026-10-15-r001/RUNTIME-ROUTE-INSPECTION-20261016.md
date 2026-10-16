# Runtime route inspection — 16 October 2026

## Finding

No supported, non-inference route was found that reports the complete set of tools actually registered for a `codex exec` turn, and no actual tool-denial canary was run. Keep `runtime_capabilities` unavailable and the worker-dispatch gate closed. The app-server protocol has an MCP-only status route, but its schema does not make it a complete `codex exec` tool inventory; it was not invoked.

## Read-only inspection

Installed binary: `C:\Users\aidan\AppData\Local\OpenAI\Codex\bin\9614f1d9b40d9c4f\codex.exe`; `--version` returned `codex-cli 0.162.0-alpha.17.2`.

Commands used (help/schema inspection only):

- `codex --help`
- `codex exec --help`
- `codex debug --help`
- `codex debug app-server --help`
- `codex debug prompt-input --help`
- `codex app-server --help`
- `codex app-server generate-json-schema --help`
- `codex app-server generate-ts --help`
- `codex app-server generate-json-schema --out <unique directory under %TEMP%>`

The generated static protocol schema lists app-server methods including `mcpServerStatus/list`, `skills/list`, `thread/start` and `turn/start`. The `McpServerStatus` response schema has a `tools` map and `toolsError`, so an app-server status request can expose the connected MCP servers' discovered catalogs. This is only an MCP-server catalog, not the full built-in/model-facing tool set for a separate `codex exec` invocation. The thread-start response contains thread settings and a thread object; turn-start returns a turn. Neither schema provides a complete registered-tool inventory. The protocol request catalog contains no general `tools/list` method; `mcpServer/tool/call` is an execution method and was not invoked.

`codex exec --help` documents sandbox, approval, JSON events, output schema and ephemeral options, but no dry-run or tool-inventory mode. The earlier `debug prompt-input` result remains input-only per `RUNTIME-INSPECTION.json`; disabled feature flags and read-only sandbox settings therefore remain requested controls, not measured tool removal.

## Boundaries and unknowns

No `codex exec`, model turn, app-server daemon request, MCP tool call, login/account check, credential read, or sandbox probe was performed. The static schema describes protocol shapes; it does not establish which tools a live turn would register or whether a particular deny rule is enforced. I did not test the status route because that requires an app-server request and would inspect live configured runtime state; I did not find a no-model route that covers built-in tools for `codex exec`.

The only next evidence that would change the gate is a supported observation of the exact worker invocation's effective tool inventory or an enforced denial test that exercises each relevant capability without a model call and without reading account state. Until then, the existing fail-closed behavior is warranted.
