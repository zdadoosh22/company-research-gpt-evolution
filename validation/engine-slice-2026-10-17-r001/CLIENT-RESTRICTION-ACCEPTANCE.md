# Client restriction acceptance — 17 October2026

Main Sol engineering decision, superseding the unresolved client-control
conclusion in this stage's earlier RUNTIME-FINDINGS.md and ENGINEERING-REVIEW.md.
Their measurements and failed attempts remain preserved. This accepts a bounded
client configuration, **not research, subscription/model availability, backend
identity, server-side tool behavior or trading readiness**.

## Measured boundary

The installed0.162.0-alpha.17.2 binary is pinned by SHA256
`e98c516f1c8935789aabe9122ee7e05ec4c3efd1ba6acf179242e031c495b99e`.
The exact two selected model-capability entries are frozen privately under
`state/research-engine/runtime/`; source hash
`3096c0167d00a39847a269fdcd81dfcf105c660f43e368421dc5655cee9e51d1`.
Account identity, ETag, authentication and unrelated models were excluded.
Public evidence contains the hash and selected capability fields, not the full
generic model-instruction payload. The source file must be available locally;
missing or changed bytes fail closed.

Both selected model entries specify code_mode_only. The shared argument factory
pins the staged catalog file, disables its Code Mode host, shell/browser/apps/
plugins/MCP/agent tools, disables web search, ignores user/project instructions
and user configuration, and uses an ephemeral context. Requested/reportable model
identity remains separate. Listed experimental clock/message capabilities are
retained in the public capability record; they were not offered in the observed
requests. No unknown feature name is invented to claim those were disabled.

The factory also selects the previously measured MXC read-only packet profile,
with minimal OS read exceptions, explicit Windows Temp denial and command network
disabled. It no longer combines that profile with the older `--sandbox read-only`
switch. Minimal OS roots are not claimed absent. Hosted tools do not derive
their restrictions from that command sandbox.

`PINNED-CLIENT-CANARY-r003.json` measures this actual installed client with the
pinned full catalog for **each** selected model. Each process made exactly one
local synthetic Responses request; no authentication, model, forwarding or
external inference service was involved. Both omitted the optional tools field.
This means no tool definitions were offered; the record explicitly distinguishes
omission from a serialized empty array. An explicit null/object field, extra
tool, wrong model/path, duplicate/missing request, timeout or catalog mutation
is refused. The earlier unpinned script normalized omission to[] and did not
record field presence; it cannot establish that an explicit array was present.

`ADAPTER-CLIENT-VERIFICATION-r004.json` records the production verifier performing
the same measurement itself. Its verified_live flag means actual local client
measurement, **zero inference**, not a live subscription inference or backend
attestation. Settings acceptance alone is not the basis of this acceptance.
The real worker uses the same catalog/profile factory, rechecks binary and
catalog before dispatch, receives only staged packet/schema/technical catalog,
and refuses actual tool or unknown events. User-provided ready flags cannot
replace that measurement. Subscription authentication is checked separately
before an explicitly authorized job.

## Repairs and verification

Direct parent review caught three material first-draft faults before any real
worker: an inline catalog string where CLI expects a file path, invalid feature
names mistaken for capability names, and aggregate request matching that could
hide a missing request from one process. Those are repaired with staged-byte
hash checks, a shared factory and per-process request validation. Full selected
metadata is kept private. A socket timeout bounds diagnostic shutdown.

The first two actual pinned-canary attempts failed: the parser initially rejected
an omitted tools field, and the first failure lacked useful diagnostics. Both
failure records remain. The corrected protocol records omission explicitly;
present null/object values are still rejected. This is a request-schema
correction, not permission to accept nonempty tool lists.

The known exact pre-turn Code Mode host-disabled diagnostic is now recorded as a
restriction diagnostic. Its precise observed text alone is allowed. Other errors,
altered messages, tool/state events, a failed turn or absent completion still
invalidate the result. No host is enabled to suppress the warning.

The affected-suite invocation ran94 actual tests successfully but also reported
one loader error because the coordinator named nonexistent test_engine_cli.
`RUNTIME-INTEGRATION-TESTS-r001.txt` preserves that failed invocation. The correct
four command/integration tests subsequently passed separately in
`COMMAND-INTEGRATION-TESTS-r002.txt`. Tests cover client/capture/catalog failures,
adapter failure refusal, queue/budget/recovery, packet/record integrity and command
interfaces. No new final full regression or real analytical cycle is claimed.

## Residual limits and authority

This is client-side evidence under a pinned startup catalog and configuration.
It does not observe the subscription server's internal capabilities or guarantee
provider/model availability. Those limits are recorded rather than converted
into an impossible claim of independent backend verification. The client offers
no tools, disables the code host and refuses tool events; these are the relevant
enforceable worker capabilities for this bounded inline-packet assignment.
Any changed binary/catalog/profile requires renewed verification and review.

Official references inspected17October:
[catalog/permissions configuration](https://learn.chatgpt.com/docs/config-file/config-reference),
[Windows MXC](https://learn.chatgpt.com/docs/windows/windows-sandbox),
[security boundaries](https://learn.chatgpt.com/docs/agent-approvals-security),
[Responses tools configuration](https://developers.openai.com/api/reference/resources/responses/methods/create).
These document client configuration and tool declaration; they do not independently
certify backend behavior. The original four-attempt real-case authorization,
actual independent Astra review and separate live gates are unchanged.
