# Runtime evidence — 17 October 2026

Baseline: local engine branch at d21892f3462fad9231fabcfc455f88dea130f4f0.
Installed CLI: 0.162.0-alpha.17.2, SHA256
`e98c516f1c8935789aabe9122ee7e05ec4c3efd1ba6acf179242e031c495b99e`.
Observed Windows build:26200.9711, EditionID Core. No installation/update,
saved configuration change, credentials copied, inference or account connection.

## New supported route and direct measurements

Official documentation inspected on17October2026 (publication/version date not
established): [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox),
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[security](https://learn.chatgpt.com/docs/agent-approvals-security), and
[sample provider configuration](https://learn.chatgpt.com/docs/config-file/config-sample).
These are current documentation observations, not archived release guarantees.

The Windows documentation describes an explicit MXC selection on compatible
Windows builds, with no implicit legacy fallback for an explicit selection.
This machine meets the documented build threshold. `MXC-STARTUP.json` records
a successful harmless command with the explicit MXC setting and an empty
temporary CODEX_HOME. That establishes startup only.

`MXC-MINIMAL-FILESYSTEM.json` supplies contrary evidence: minimal OS read access
also allowed a synthetic sibling under Windows Temp. Consequently the initial
profile did **not** demonstrate packet-only file access. Do not discard this
failure or generalize a single successful deny test.

`MXC-USER-TEMP-READ.json` records denial of a synthetic user-Temp file from that
first profile. `MXC-WORKER-PROFILE.json` then records a distinct profile: staged
packet under user Temp, minimal OS read access plus workspace read, explicit
Windows Temp denial, network disabled and local binding disabled. Packet read
passed; user-Temp sibling read and packet write were denied; write target did
not exist. Sandboxed curl could not connect to an actually listening loopback
sentinel, while the unsandboxed control reached it. Zero sandboxed hits were
observed. The sentinel server was closed after the test.

This is measured command/child access control for those tested objects, not an
exhaustive filesystem audit or hosted-tool restriction. Minimal OS roots remain
readable by design. Hosted search, MCP, apps and code-host tools require separate
consideration. The production adapter still selects its older read-only worker
profile; the MXC command tests cannot attest that different invocation.

## Synthetic serialized tool inventory

`tool_manifest_canary.py` is a bounded reproducible diagnostic. It creates an
empty temporary CODEX_HOME, passes only an environment allowlist, points a
custom unauthenticated provider at127.0.0.1 and sends a synthetic prompt. Its
local server records tool names/types/schema hashes, returns HTTP400 and never
forwards anything. No model service exists behind it. It does not use or inspect
subscription authentication and is not a paid API fallback.

`SYNTHETIC-TOOL-MANIFEST.json` records one local POST to `/v1/responses`, requested
model label `gpt-6.1-sol`, an empty serialized tools array, and expected process
exit1 after the synthetic rejection. The CLI also emitted a nonfatal code-mode
host-disabled error before attempting that request. Preserve that error: the
current adapter's output audit would reject such an event. No successful worker
or research result is demonstrated.

The empty tools array establishes this exact custom-provider request's client
serialization. It does not establish identical capability discovery for ChatGPT
subscription authentication, Astra, another model catalog or server behavior.
Neither requested flags nor an inferred common code path establishes that
equivalence. The runtime verifier therefore remains unavailable; no ready flag,
unrestricted worker, inference probe or analytical acceptance was substituted.

## Decision and bounded continuation

The older blanket statement that Windows packet restriction cannot start is
superseded **for the tested MXC command profile only**. Historical legacy failure
records remain intact. Tool/profile equivalence for the actual subscription
worker remains unresolved. All four real-case inference attempts remain unused.

The highest-value next runtime action needs a supported way to observe or enforce
the actual subscription worker's tool surface, then centrally select and test
that same restricted invocation. Do not repeat debug prompt-input, legacy
sandbox failures or the synthetic400 merely to obtain a different result. Do
not weaken the requirement or repeat closed company audits while it is blocked.

Parent inspection also corrected the adapter's dated blocker metadata; no
positive capability attestation was added. Its24 focused tests passed on this
revision, including unavailable-runtime refusal before authentication/dispatch,
tool-event refusal, model substitution and timeout/quota handling. This is
engineering evidence, not analytical review or live isolation verification.
