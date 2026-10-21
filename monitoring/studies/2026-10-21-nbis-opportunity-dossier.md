# Short-Horizon Opportunity Dossier: NBIS (Nebius Group N.V.)
**As of Date:** 2026-10-21
**Mandate:** £300 Trading 212 ISA Model Sleeve (Max £100.00 commitment; £75.00 binary cap if earnings <14d)
**Security:** NASDAQ:NBIS (ISIN NL0009805522)
**Quote Currency:** USD | **FX Rate:** 0.7467 GBP per USD | **Current Price:** $171.57

---

## 1. Executive Summary & Catalyst Mechanism
- **The Event/Catalyst:** Q3 2026 earnings release expected late October / early November 2026; major data center capacity online milestones in Europe/US.
- **Business Impact:** Hyper-growth GPU cloud infrastructure provider. Q2 2026 revenue surged +454% YoY to $582.3M with annualized run-rate (ARR) hitting $3.0B. Order backlog stands at an immense >$40B.
- **Market Expectations vs. Reality:**
  - Consensus expects Q3 2026 revenue of ~$904.8M (up ~55% sequentially from Q2).
  - Trading at $171.57 after a rapid run-up. While revenue growth is staggering, GAAP profitability is still heavily negative ($(190.4)M GAAP net loss in Q2).

---

## 2. Statutory-to-Owner Cash Flow & Valuation Bridge
- **Statutory GAAP vs. Management Non-GAAP:**
  - Q2 GAAP Net Loss: $(190.4)M vs. Adjusted EBITDA of $236.2M.
  - Huge bridge delta: Depreciation & Amortization of GPU clusters ($148M), Stock-Based Compensation ($75M+), and finance costs.
- **The CapEx Reality (Owner Cash Flow Burn):**
  - Building AI superclusters is capital-intensive. Operating cash flow before working capital is positive ($180M+), but quarterly CapEx exceeds $600M+.
  - **Free Cash Flow to Equity (FCFE):** Deeply negative (cash-consumptive phase funded by cash reserves and debt/convertible facilities).
- **Liquidity & Net Cash Buffer:**
  - Post-restructuring cash and liquid reserves exceed $2.2B, providing a 3–4 quarter runway at current buildout velocity without urgent dilution.
- **Fair Value Scenario Matrix:**
  - **Bear Case ($120.00):** GPU rental pricing pressure from hyperscalers (Azure/AWS/GCP), delivery delays on high-end clusters, multiple derating (-30.0%).
  - **Base Case ($220.00):** Q3 revenue prints ~$920M+, ARR reaches $3.8B+, backlog expands (+28.2%).
  - **Bull Case ($280.00):** Tier-1 AI lab sovereign cloud multi-billion commitment announced (+63.2%).

---

## 3. Trading 212 Sleeve Economics, Options Positioning & Hurdle Check
*Calculated using `tools/engine.py math` and `tools/engine.py options`:*
- **Current Share Price:** $171.57
- **Options & Dealer Gamma Positioning (Expiry 2026-10-23):**
  - Spot: $171.57 | Max Pain: $180.00 (+4.9% above spot).
  - Top Call Walls: $200.00 (7,882 OI), $230.00 (7,781 OI).
  - Top Put Walls: $165.00 (4,443 OI), $155.00 (3,777 OI), $150.00 (3,510 OI).
  - Net Dealer GEX: +$0.09M (neutral to slightly positive gamma).
  - ATM Straddle Move: $\pm$6.5% weekly implied volatility.
- **Hurdle Analysis at $171.57:**
  - Commitment: £75.01 (0.5846 shares) under binary catalyst cap.
  - Break-even: $172.09 (+0.30% to clear FX fee).
  - Target ($220.00): Net £95.89 (+£20.88 / +27.84% net).
  - Hard Stop ($145.00, below key $150 Put Wall): Net £63.20 (-£11.81 / -15.74% net).
  - Upside-to-Downside Ratio: **1.77:1** (Fails >2:1 hurdle requirement at $171.57).
- **Strict Entry Ceiling Solve:** **$169.49** (or **$165.00** at the primary Put Wall).

---

## 4. Mandatory Adversarial Challenge (Astra Red-Team)
- **Extreme Capital Intensity:** NBIS is not a recurring SaaS business—it is an infrastructure utility that must continuously buy billions in cutting-edge silicon with a rapid depreciation cycle (3–4 years).
- **Binary Cloud Customer Concentration:** A large portion of early AI cloud contracts can be lumpy or subject to renegotiation if inference cost curves collapse.
- **Volatility Risk:** With high beta and negative FCF, any macro tech pullback hits NBIS harder than cash-generative mega-caps. At $171.57, entering before a clean dip to the $165 put wall exposes the sleeve to a 15% drawdown on 1.77:1 odds.

---

## 5. Output Contract & Structured Verdict
- **VERDICT: WATCH / LIMIT TRIGGER, NBIS, buy only at or below $165.00.**
- **Rationale:** Spectacular +454% YoY top-line growth and $40B backlog, but negative free cash flow and a 1.77:1 upside/downside ratio at current market price fail the risk mandate. The key support floor and entry ceiling is $165.00 (top put wall).

### Telegram Alert Payload
```text
WATCH / LIMIT TRIGGER | NBIS (Nebius Group) NL0009805522
Buy ONLY at or below $165.00 (strict math ceiling $169.49; now ~$171.57).
Catalyst: Q3 earnings late Oct/early Nov 2026. Consensus rev ~$904.8M (+55% QoQ). ARR ~$3.0B, backlog >$40B.
Why not now: Base gain is +27.8% net but upside/downside is 1.77:1 (needs >2:1). CapEx cash burn requires high margin of safety.
If triggered <=$165.00: GBP 75 (binary event cap), stop $145.00, target $220.00, thesis exit if ARR growth slows <30% QoQ or cluster deployment faces major power delays.
Friction: 0.15% FX each way; break-even ~+0.30%.
```
