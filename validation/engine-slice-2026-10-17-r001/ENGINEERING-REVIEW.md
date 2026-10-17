# Parent engineering review — 17 October 2026

Reviewed directly by the main Sol agent; narrow Luna agents supplied provisional
requirement mappings and a diagnostic-design criticism. No Astra analytical
review is implied. Baseline d21892f3462fad9231fabcfc455f88dea130f4f0; exact changed
file hashes are bound by the stage checkpoint/assessment, not an invented final
commit identifier.

## Adapter metadata correction — accepted, no worker enablement

The only production source change updates `runtime_capabilities` documentation,
blocker strings and dated evidence paths. The return remains unavailable,
verified_live=false, tool_inventory=null and inference_calls=0. The actual
dispatch guard and invocation are unchanged. An old failed legacy sandbox is
not described as evidence against every supported Windows backend. Conversely,
successful MXC command tests and a custom-provider empty-tool request do not
permit the actual subscription worker to run. No caller-provided capability
flag or unrestricted agent substitutes for the missing verifier.

The24 adapter tests passed after the change (unittest discovery,
test_scoped_research_adapter.py;1.717seconds). The focused run includes refusal
before auth/worker/claim when unavailable, unauthorized events, substitution,
credential-like output, target mutation, replay and partial results. The
413-test/412-pass/1-skip regression remains dated16October evidence for the
previous executable revision. A final release regression remains outstanding;
do not represent the focused run as a new full regression.

## Synthetic diagnostic — accepted for its bounded observation only

Inspected `tool_manifest_canary.py` directly. Inputs are a synthetic string,
installed executable path and an empty temporary account directory; environment
keys are allowlisted. The custom provider endpoint is constructed from a server
bound only to127.0.0.1. There is no forwarding, account authentication or actual
model behind it. It rejects the one captured request with400. The server is
closed in finally; the temporary account directory is scoped by a context
manager. The returned failure and code-mode error are preserved, not relabelled
as a successful research job. Output contains tool metadata and synthetic
diagnostic output, not request headers or real credentials.

Residual limits: this one-off probe is not production transport, an exhaustive
network monitor or a subscription-tool attestation. The capability inventory
depends on provider/model/session setup. A local serialization test cannot prove
server-side behavior. No positive runtime gate is justified by it.

The separate MXC network test used a live loopback listener and unsandboxed
control. A provisional delegated comment described the listener as absent; that
interpretation is rejected by the parent because the recorded control and
test lifecycle establish that it was listening during the sandbox attempt.
This correction does not expand command-level evidence into hosted-tool proof.

## Requirement audit and protected boundaries

Delegated mappings must be reconciled with every exact original requirement;
group status is provisional. In particular, running an evaluation is distinct
from passing its recall criterion, fixture behavior from real execution, and
an earlier regression from final release verification. The known4/5 recall
failure and missing real Sol/Astra cycle remain visible. Historical artifacts,
sources, methodology and closed company dispositions are preserved.

The three issuer notices captured this stage are a preliminary schedule refresh
only. They are not an exhaustive disclosure check, full candidate selection,
post-event investigation, fresh financial conclusion or executable quote. No
price, investment recommendation, paper fill, broker connection, phone setup,
monitoring change or live gate acceptance follows. No model inference attempt
from the four-call real-case budget was consumed.
