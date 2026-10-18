# Client recovery engineering disposition — 18 October 2026

Accepted for the bounded client route: replacement version/hash, shared-profile zero-inference tool inspection, and controlled filesystem/network checks. Evidence is in CANDIDATE-CLIENT-INSPECTION-r002.json, CANDIDATE-SANDBOX-r003.json, ADAPTER-CANDIDATE-VERIFICATION-r002.json and INTEGRATION-r001.json. Earlier failed/interrupted measurements remain historical; r003 supersedes the startup-only sandbox results for restriction assessment.

The timeout repair addresses a reproduced inherited-pipe failure, verified by an actual sleeping parent/child fixture. The original stalled probe's exact cause is not proven; another untraced probe needed interruption while the subsequent traced probe returned verified promptly. Further diagnosis or an outer process watchdog remains necessary before claiming a general no-hang guarantee. New pin acceptance is technical only. No real model review completed, no gate activated, no API route enabled.

Official documentation inspected: https://learn.chatgpt.com/docs/windows/windows-sandbox (redirect from https://developers.openai.com/codex/windows/), retrieved18October2026. It describes Windows sandbox configuration; it is not proof of this exact alpha binary's behavior. Installed sandbox --help confirms the direct command interface. An initial incorrect `sandbox windows --help` invocation failed trying to launch `windows`; it was not a capability test.

The approved brief's overall goal remains active. Current scope includes a tested explicit one-review extension, actual independent review/disposition, final engineering acceptance and the full419-item audit. Frozen retrieval's failed gold item remains failed; no trading edge or live readiness claim.
