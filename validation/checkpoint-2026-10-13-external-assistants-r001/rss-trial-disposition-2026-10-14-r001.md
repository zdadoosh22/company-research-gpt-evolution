# Offline RSS trial disposition

Reason: the verified 6 October Uber acquisition announcement appeared in the official issuer RSS while the inspected SEC submissions metadata stayed unchanged. This demonstrates a channel-coverage gap, not permission to activate monitoring.

First module: 178 source lines as transcribed; the author's subsequent claim of approximately 207 lines was not verified and conflicts with this artifact. Actual results: 41/44 passed. Two failures concerned missing/blank titles: the consumer's requirement was clarified because RSS can permit description-only items. The material original failure was financial comparison loss: `Net cash < 5 and debt > 9` versus `< 4` produced the same digest after broad tag stripping. Retain original code and result; do not call this a clean first pass.

Prompted successor: conservative digest over XML-decoded fields with control/whitespace normalization only; display titles unescape once and preserve comparisons as passive text. Stable identities unchanged; digest version changes, so v1/v2 hashes must not be compared as substantive revisions without rebaselining. Markup changes can create triage false positives. No perfect HTML semantics claimed. Consumers must not render returned titles as HTML.

Work results: same 44-case harness passes 44/44. Three additional title checks pass: visible comparisons retained with a changed digest and stable ID, empty tag-only title rejected, punctuation-only title rejected. Actual retained ten-item issuer feed parsed deterministically with unique identities and UTC dates. Each run rechecked all fourteen frozen Uber inputs. DTD handling across UTF-8/BOM/UTF-16, malformed versus genuinely empty feeds, duplicate conflicts, dates, size limits and passive injected instructions were included; see complete case results and harness.

Blind external test design supplied twelve categories, without seeing the implementation; Work added substantive comparison and robustness cases. Neither external conversation executed code. Tests are offline, mostly synthetic; no observations of future news, paper fills, network fetches by the module, accounts or orders.

Decision: retain as a verified narrow prototype pending adversarial field-extraction checks and later separately scoped production integration. Namespace interpretation, child-text joining, baseline migration, source identity, persistence, retries and live coverage remain outside this acceptance. No operational configuration modified.
