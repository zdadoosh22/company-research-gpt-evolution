# Subscription-only research hold

11 October 2026. The user has instructed this Work goal to use only the included subscription allowance and stop with about 1% of the five-hour allowance remaining. Credits, paid model APIs, purchases and automatic quota resets are not authorised.

The existing observation adapter authenticates through the subscription, but that authentication does not itself prohibit use of available account credits after included limits. The available usage tool reports account limits; it does not expose a per-chat hard credit-block setting. A request can consume usage between observations, and other chats share the allowance. Exact stopping precision therefore cannot be guaranteed.

Set `research_enabled` to false and restart the existing observation daemon so its in-memory configuration observes the hold. This holds automatic observation model drafts, not deterministic source checks, event queues, ledger records or manual research in the current Work goal. Preserve queued jobs. Do not automatically re-enable them when quota resets. The separate scoped research queue has no background worker and no job is launched there by this change.

Actual restart limitation: the task reported Running before the stop, but its scheduled-task settings were disabled. Starting the task then failed because it was disabled. Its enabled setting and triggers were not changed. The existing daemon was relaunched directly with the same bundled windowless runtime and project script, hidden, to retain source checks with the held-model configuration. This is current-process recovery, not restored scheduled startup or proof of future uptime. Record and verify the resulting process; do not describe the scheduled task as Running afterward.

During the Work goal, inspect included usage before substantial model/review batches; keep batches small near exhaustion and reserve enough allowance to save a verified continuation. Never switch to an API key, purchase credits, use a free reset without instruction, or launch another review when the remaining allowance cannot plausibly cover it. If the usage service is unavailable near the boundary, stop model work rather than assume remaining subscription capacity.

The hold is an operational cost boundary, not a research approval, strategy change or guarantee of account-wide billing controls. Other user-owned chats remain outside this project's control. Its verification is recorded separately; ordinary subscription-authenticated review still requires actual independent findings and evidence.

Source: [official pricing and usage documentation](https://learn.chatgpt.com/docs/pricing), inspected 11 October 2026, sections “What happens when you hit usage limits?”, “What are tokens and credits?” and shared usage allowances. Available account credits can extend work after included limits; no model API route is used here.
