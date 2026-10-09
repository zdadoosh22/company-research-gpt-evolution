# £300 research observation

This extension monitors a small research-validation watchlist and keeps a separate manual portfolio ledger. It does not trade, activate real investment recommendations, use unrelated ISA holdings, or turn partial pilots into trading signals.

## Current boundary

The user confirmed the isolated £300 allocation on 7 October 2026. The ledger records £300 cash from that declaration; actual broker cash has not been independently verified and no transfer occurred. The objective is aggressive growth over days to a few months, with no need for intraday trading. Numerical sizing/exit rules remain unvalidated. APP/JPM/Unilever are validation subjects, not chosen investments. Real recommendations have no activation command in this version. See [IMPROVEMENT-ROADMAP.md](IMPROVEMENT-ROADMAP.md) for the staged short-term strategy research and acceptance work.

The local status panel is `state/observation/status.html`. It is a dated snapshot, refreshed by the service; check its last tick. Operational records and source archives live in `state/observation/`, excluded from Git. The configured cadence is 09:00 and 18:00 Europe/London. The target pause between service passes is 30 seconds; source/network work can delay Telegram polling and backups. Model research runs separately, one job at a time.

The detailed snapshot distinguishes each source's last attempt, success and failure. The aggregate successful-pass timestamp means every configured source succeeded together; it may be absent while individual feeds work. `tools/observation_trial_report.py` reads actual check history without changing the ledger. It reports observed gaps and elapsed wall time, with continuous uptime and acceptance explicitly unestablished. See `validation/operational-evidence-2026-10-09.json` for the dated first report.

The Windows task is `CompanyResearch2-Observation`, running without a visible window under your signed-in user. It starts at sign-in and at the daily recovery times. A locked signed-in session can continue. It cannot run while Windows is asleep, powered off, or before you sign in after restart. No sleep, auto-login or power settings were changed. Internet is required for source checks, Telegram and model research.

## Phone setup still needed

1. Create a private bot through Telegram's official BotFather and obtain its token. Never paste the token into research records or chat.
2. Obtain your numeric private Telegram user/chat ID. Groups are rejected. Only that user can submit commands.
3. From this project, run `./tools/observation.ps1 configure-telegram`. It asks for the token with hidden input and stores a Windows-user-protected DPAPI file. No credentials enter the database or its backups.
4. Open the bot chat and send `/start`. Enable iPhone notifications for Telegram and this chat; check Focus/mute settings.
5. Test a locked-phone message, delayed reading, status request, withdrawal, and failed/offline status. API acceptance alone does not prove phone delivery or reading.

Both bot setup and the actual iPhone test remain unverified until completed. Telegram chat history is cloud stored; it is not an end-to-end encrypted secret chat. Minimise sensitive content. The bot never receives your Trading 212 login or key.

## Manual records

Run commands from the project folder using `./tools/observation.ps1 ...`. They only record your reports; none places or cancels broker orders.

| Command | Meaning |
|---|---|
| `status` | Local state, blocked gates, jobs and failures |
| `fund --amount 300` | Explicitly confirm the planned allocation has been ring-fenced; no transfer occurs |
| `quote monitoring/examples/quote.json` | Import a quote after replacing all example fields and timestamps |
| `fx-quote FILE.json` | Supply dated GBP per one foreign major currency unit; template under monitoring/templates/manual-fx-quote.json is stale synthetic evidence only |
| `trial-alert monitoring/examples/trial-alert.json` | Create a clearly labelled nonactionable test notice |
| `ack ALERT-ID` | Acknowledge notice; not a fill |
| `withdraw ALERT-ID "reason"` | Withdraw local notice; standing broker orders remain your responsibility |
| `order ALERT-ID buy SECURITY-ID QUANTITY --reserve-gbp TOTAL --order-id BROKER-ORDER-ID` | Reserve sleeve cash including fees for a manually placed order |
| `order ALERT-ID sell SECURITY-ID QUANTITY --order-id BROKER-ORDER-ID` | Reserve only sleeve-owned shares |
| `fill ORDER-ID EXECUTION-ID QUANTITY GBP-VALUE --fees-gbp GBP-FEES` | Record an actual fill; GBP value excludes separately supplied fees |
| `cancel ORDER-ID` | Record your confirmed broker cancellation; does not cancel it remotely |
| `cash-event EVENT-ID dividend GBP-AMOUNT --ticker SECURITY-ID` | Record a dividend on currently recorded sleeve holdings |
| `cash-event EVENT-ID fee GBP-AMOUNT` | Record a separate sleeve fee without duplicating fill fees |
| `retry-job JOB-ID` | Explicitly requeue an interrupted/deferred research job |
| `reconcile "note"` | Record reconciliation of missed fill reports and outstanding orders |
| `backup` | Create today's database backup |

Use an exchange-qualified security ID consistently (`EXCHANGE:TICKER` or `EXCHANGE:TICKER:CLASS`), with the same identifier in quotes and orders. Plain ticker records remain unverified and cannot establish NAV. A well-formed broker fill outside the reported cash reservation, with an unknown order or conflicting execution ID is retained as an unverified reconciliation exception. It does not charge unrelated ISA cash. Unresolved exceptions make NAV unknown; exact successful replay resolves only the matching report. A generic reconciliation note cannot erase these exceptions. Historical dividend entitlement after you sold all recorded shares needs separate reconciliation; this version does not infer entitlement dates.

Telegram supports `/status [ALERT-ID]`, `/ack ALERT-ID`, `/order ALERT-ID buy|sell SECURITY-ID QUANTITY GBP-RESERVE ORDER-ID`, `/fill ORDER-ID EXECUTION-ID QUANTITY GBP-VALUE GBP-FEES`, and `/cancel ORDER-ID`. For a sell report use `0` as the GBP reserve. Reports count only after receiving the bot's confirmation. No response means the local system has not confirmed receipt.

All current delivered alerts are trials. They cannot supply a current trading confirmation, even if fresh. The separate decision pipeline now tests reservation-backed confirmations with all evidence gates, including the portfolio decision itself. It remains paper-only and requires trusted current-fact validators. No live instruction is enabled by waiting fourteen days or editing config.

## Sources and research

The delegated readiness standard and scoped days-to-months research route are described in `monitoring/DECISION-SCOPE.md`. `tools/paper.py FILE.json` exposes the isolated prospective comparison engine; its operation/arguments records use the exact `PaperStudy` method names. It does not supply market inputs or fabricate fills. `tools/decision_pipeline.py` connects actual artifact verification to the separate paper decision ledger; it requires externally verified current facts and capital/group-exposure proofs, rather than self-declared flags. Both remain separate from live observation delivery until acceptance conditions pass.

Six SEC submission feeds establish issuer-checked filing baselines: APP, JPM and Unilever as validation subjects, plus AMD, Uber and Netflix as discovery subjects. The latter three were added on 9 October with fresh baselines; historical filings did not create alerts or research jobs. The frozen cohort and its source identities are recorded in `monitoring/research-universe-2026-10-09.json`. None is a selected investment. Later relevant accessions queue focused read-only research; existing pending changes for a company consolidate. Discovery jobs use explicitly configured saved studies without creating an approved company run. Unilever results and regulatory pages are also configured, but retrieval failures are exposed, not interpreted as no change. These SEC feeds do not establish comprehensive news, immediate earnings-release or UK announcement coverage.

Source archives retain URLs, retrieval times and hashes. A detected page change is unclassified, not automatically material. Missing quote acquisition means there is no independent real-time price-opportunity detection. You can manually set Trading 212 recurring price alerts as a supplement, but they do not check research validity.

Codex is subscription-authenticated, pinned to GPT-6.1 Sol High, standard speed, read-only and live search. It cannot publish company runs or approve allocations. Results are drafts under `state/observation/research/`, always awaiting review. An actual Astra review is distinct from engineering review and remains required where the methodology requires it. Gemini CLI/entitlement/quality validation remains pending; no Gemini installation or paid API fallback occurs automatically.

Failed research attempts preserve continuation and back off six hours, deferring after five attempts. Service restart marks abandoned running work interrupted; inspect saved work before `retry-job`. Repeated provider calls without successful approval never produce trade authority.

## Reliability and acceptance

Database writes, update deduplication and staged replies are atomic. A single engine lock excludes overlapping service ticks. Uncertain sends are not blindly resent; their outcome needs inspection. Withdrawal edits delivered originals and sends a separate notice; pending active originals are superseded. Old phone previews remain historical.

Daily opening snapshots copy only SQLite data, not DPAPI credentials. A separate latest-ledger copy refreshes on service passes after manual records change. These are local recovery snapshots, not an off-device disaster backup. After more than 24 hours offline, incoming Telegram reports may have expired; resend unconfirmed reports and reconcile the broker. A disconnected computer cannot send an immediate outage or discover invalidation. Status snapshots never imply comprehensive live coverage.

Before actionable development: verify the actual phone, complete at least 14 days of observed operation and failure injections, finish relevant company research acceptance and model review, define the portfolio policy, and validate quote coverage. No time-only promotion exists. NAV/weights use fresh, exchange-matched manual security marks. Foreign prices require an explicit dated FX snapshot in GBP per one major currency unit; both snapshots must pass freshness checks. Missing, stale or ambiguous marks leave totals unknown. Gross NAV excludes hypothetical future liquidation costs; actual fill costs enter the cash ledger. These manually supplied snapshots do not establish unattended price coverage or authority to trade.

Stop/start through Windows Task Scheduler. To remove the task: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/register-observation-task.ps1 -Remove`. The helper verifies the action, stops the task and checks it has stopped before unregistering it. If stopping fails, it preserves the registration. Windows PowerShell on this machine blocks script files by default; the shown flag applies only to that launched process and does not change the saved execution policy. Local records remain on disk. The equivalent command without `-Remove` registers the task; then start it through Task Scheduler.

## Official references

- [Codex subscription authentication](https://learn.chatgpt.com/docs/auth), [unattended execution](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Gemini authentication](https://geminicli.com/docs/get-started/authentication/), [subscription quotas](https://geminicli.com/docs/resources/quota-and-pricing/)
- [Telegram API and update retention](https://core.telegram.org/bots/api), [free ordinary bot messaging](https://core.telegram.org/bots/faq)
- [Trading 212 API](https://docs.trading212.com/api), [price alerts](https://helpcentre.trading212.com/hc/en-us/articles/360008878817-What-are-price-alerts-and-how-do-I-use-them), [FX fee](https://helpcentre.trading212.com/hc/en-us/articles/360018909758-What-is-the-FX-fee-Invest-Stocks-ISA)
