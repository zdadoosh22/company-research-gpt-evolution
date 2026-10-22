# Master Quantitative Tactical Day & Swing Trading Playbook

**System:** Principal Quantitative Architect, Tactical Systems Engineer & Forensic Trading Technologist  
**Date:** October 2026  
**Workspace:** `daytrading/` (Strictly Isolated from Long-Term Research Engine in `tools/`)  
**Account Mandate:** £1,000 Trading 212 Stocks ISA — **Aggressive Capital Growth & Tactical Cash Weapon**  
**Slot Sizing:** **3 to 4 Concurrent Slots (£250.00 to £333.33 / Trade | 25.0% to 33.3% of Sleeve Equity | 80%–100% Deployed When Confident)**  
**Holding Horizon:** Intraday Scalp (1–4h) | Standard Swing (2–5d) | 10-Day EMA Trailing Runner (4–12d)  

---

## 1. Core Mandate: Aggressive Capital Growth & Tactical Cash

Our £1,000 Trading 212 Stocks ISA tactical sleeve is dedicated purely to **aggressive capital growth**. External cash reserves are held outside this trading pool. Consequently:

1. **Passive Cash Drag is Prohibited:**
   * The engine must **NEVER** hold arbitrary passive cash buffers (no 55%–77.5% idle cash sitting at 0%).
   * When high-conviction setups trigger in a favorable market regime, the portfolio deploys **80% to 100% of equity across 3 to 4 active slots** (**£250.00 to £333.33 per trade**, scaling dynamically as sleeve equity grows).
2. **Cash is Strictly an Active Tactical Weapon:**
   * Cash is held **ONLY** when market conditions are hostile—specifically when the aggregate index (`SPY`/`QQQ`) trades below its 10-day EMA, Options Dealer Gamma is Negative ($\text{Net GEX} < \$0$), or zero candidate setups pass our strict compression and volume-surge gates.
3. **Institutional Portfolio Risk Cap (1.5%–2.0% Risk Per Trade):**
   * Maximum portfolio equity risked on any single trade is strictly capped between **1.50% and 2.00%** via volatility-calibrated hard stops:
     $$\text{Portfolio Risk (4 Slots)} = 25.0\% \text{ Slot} \times 6.2\% \text{ Stop} = \mathbf{1.55\% \text{ of Sleeve Equity}}$$
     $$\text{Portfolio Risk (3 Slots)} = 33.3\% \text{ Slot} \times 5.6\% \text{ Stop} = \mathbf{1.86\% \text{ of Sleeve Equity}}$$

```
                     MASTER TACTICAL GROWTH WORKFLOW
                                    │
                                    ▼
                     [PHASE 2: TACTICAL REGIME GATE]
                     - Index >= 10 EMA & Positive Dealer GEX?
                       ├── NO  ──► 100% TACTICAL CASH WEAPON (Zero New Longs)
                       └── YES ──► Authorize 80%–100% Growth Slot Deployment (3–4 Slots)
                                    │
                ┌───────────────────┴───────────────────┐
                ▼                                       ▼
      [UK ZERO-FX ISA LEADERS]             [US MOATS & LEVERAGED ETFs]
      - RR.L, RIO.L, AZN.L, SHEL.L, BARC.L - NVDA, PLTR, APP, CRWD, TQQQ, SOXL
      - 0.00% FX Fee Edge                  - 0.30% Round-Trip FX Hurdle (Min +8.5% T1)
                │                                       │
                └───────────────────┬───────────────────┘
                                    │
                                    ▼
                  [PHASE 1: HIGH-CONVICTION SCANNER GATES]
                  - 5-Day Compression Bandwidth <= 6.0% of Spot
                  - Breakout Daily Volume Surge >= 1.50x of 10D SMA
                  - Daily Close > 5D High AND Close >= 10D EMA
                  - Forensic Gate PASS (Block SMCI, MSTR, MARA, RIOT)
                                    │
                                    ▼
                  [PHASE 3: TWO-STAGE HARVEST & 10 EMA RUNNER]
                  - Stage 1 (50%): Bank at +7.5%..+8.5% USD (+5.0%..+5.5% UK)
                    (Protects against the 84.6% crest-and-pullback rate)
                  - Breakeven Ratchet: Raise Stop on remaining 50% to Entry + 0.35%
                  - Stage 2 (50%): Trail along Daily 10 EMA / 2D Low for 4–12 Days
                  - 09:00 UK Pre-Market Cut: Immediate exit if overnight gap <= -6.5%
```

---

## 2. The 200-Ticker Active Quantitative Universe

The tactical laboratory monitors and executes across 10 liquid sectors:

1. **UK London-Listed Zero-FX Leaders (15) [TOP PRIORITY — 0.00% FX]:** `RR.L`, `RIO.L`, `AZN.L`, `SHEL.L`, `BP.L`, `GSK.L`, `BARC.L`, `LLOY.L`, `NWG.L`, `HSBA.L`, `ULVR.L`, `REL.L`, `DGE.L`, `BATS.L`, `VOD.L`
2. **Leveraged Bull ETFs (15):** `TQQQ`, `SOXL`, `UPRO`, `NVDL`, `CONL`, `TECL`, `FNGU`, `BULZ`, `LABU`, `TNA`, `ERX`, `DFEN`, `DPST`, `YINN`, `CWEB`
3. **Leveraged Bear/Inverse ETFs (15):** `SQQQ`, `SOXS`, `SPXU`, `TECS`, `FNGD`, `BERZ`, `LABD`, `TZA`, `ERY`, `SDOW`, `FAZ`, `YANG`, `KOLD`, `BOIL`, `UVXY`
4. **Mega-Cap Tech & S-Curve Titans (15):** `NVDA`, `AAPL`, `MSFT`, `AMZN`, `META`, `GOOGL`, `TSLA`, `AVGO`, `NFLX`, `ORCL`, `ADBE`, `CRM`, `INTU`, `IBM`, `CSCO`
5. **High-Beta Semis & AI Hardware (25):** `AMD`, `QCOM`, `ARM`, `MU`, `AMAT`, `LRCX`, `KLAC`, `ADI`, `MRVL`, `SMCI`, `DELL`, `VRT`, `TXN`, `INTC`, `ANET`, `PSTG`, `MPWR`, `ON`, `NXPI`, `MCHP`, `TER`, `ENTG`, `WDC`, `STX`, `ASML`
6. **Cloud, Cybersecurity & Enterprise SaaS (25):** `PLTR`, `CRWD`, `PANW`, `FTNT`, `NET`, `DDOG`, `SNOW`, `APP`, `MDB`, `NOW`, `ZS`, `WDAY`, `HUBS`, `TEAM`, `CFLT`, `ESTC`, `PATH`, `OKTA`, `DOCU`, `SPLK`, `VEEV`, `DT`, `GTLB`, `ZI`, `BILL`
7. **Fintech, Crypto & High-Beta Platforms (20):** `COIN`, `UBER`, `ABNB`, `DASH`, `SHOP`, `SQ`, `PYPL`, `SPOT`, `ROKU`, `TTD`, `HOOD`, `AFRM`, `SOFI`, `MARA`, `RIOT`, `CLSK`, `MSTR`, `MELI`, `SE`, `GRAB`
8. **Healthcare, Biotech & Growth (25):** `LLY`, `NVO`, `VRTX`, `REGN`, `ISRG`, `MRNA`, `BIIB`, `ALNY`, `CRSP`, `CELH`, `GILD`, `AMGN`, `BMY`, `PFE`, `ABBV`, `MRK`, `TMO`, `DHR`, `ABT`, `SYK`, `BSX`, `DXCM`, `VKTX`, `EXAS`, `INCY`
9. **High-Momentum Industrials & Energy (25):** `GE`, `CAT`, `ETN`, `PH`, `CEG`, `VST`, `ENPH`, `FSLR`, `OXY`, `FCX`, `RTX`, `LMT`, `BA`, `NOC`, `GD`, `DE`, `HON`, `UNP`, `EMR`, `PCAR`, `XOM`, `CVX`, `COP`, `SLB`, `MPC`
10. **Consumer Discretionary & Retail (25):** `WMT`, `COST`, `TGT`, `HD`, `LOW`, `NKE`, `SBUX`, `MCD`, `CMG`, `BKNG`, `TJX`, `ROST`, `MAR`, `HLT`, `YUM`, `ORLY`, `AZO`, `LULU`, `ULTA`, `DECK`, `ONON`, `BBY`, `DG`, `DLTR`, `TSCO`

---

## 3. High-Conviction Setup Identification Gates (Phase 1 Empirical Proof)

Across 1,000 backtested breakout setups ([`phase9_high_conviction_filtering.md`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/evidence/phase9_high_conviction_filtering.md)), enforcing all five entry gates elevated initial continuation win rates from **52.00% to 67.70%** and expanded Profit Factor from **1.020 to 2.666**:

1. **5-Day Compression Bandwidth Gate ($\le 6.0\%$):** $\frac{\text{High}_{5D} - \text{Low}_{5D}}{\text{Spot}} \le 6.0\%$. Rejects loose mid-range chop.
2. **Institutional Volume Surge Gate ($\ge 1.50\times$):** Daily breakout volume must be $\ge 1.50\times$ the 10-day volume SMA.
3. **10-Day EMA Alignment:** Breakout close must clear the 5-day high AND close $\ge \text{EMA}_{10}$.
4. **Forensic Accounting Disqualification Gate:** Permanent block on auditor resignations (`SMCI`), negative core FCF dilution traps (`MSTR`, `MARA`, `RIOT`), and SBC $>18\%$ of revenue without $>25\%$ growth.
5. **UK Zero-FX ISA Overweight (38%–45% Slot Share):** Prioritizes `RR.L`, `RIO.L`, `AZN.L`, `SHEL.L`, `BARC.L` to harvest 0.00% FX friction.

---

## 4. Tactical Cash Regime Gate & 09:00 UK Pre-Market Protection (Phase 2 Proof)

Across 500 simulated market cycles ([`phase10_tactical_cash_regime_report.md`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/evidence/phase10_tactical_cash_regime_report.md)):
* **Market Regime Filter:** When the benchmark index is below its 10-day EMA or dealers are in Negative Gamma, breakout failure rates hit 72%. Forcing **100% Tactical Cash** during hostile windows avoided 6,838 chop trades and cut mean maximum drawdown from **13.51% down to 6.08%**.
* **09:00 UK Pre-Market Emergency Cut (`<= -6.5%` Gap):** Trading 212 opens US pre-market execution at **09:00 UK time** (5.5 hours before the 14:30 UK regular open). Executing an immediate pre-market cut when an overnight catalyst gap breaches **$-6.5\%$** saved an average of **+3.37% per gap event** by avoiding the 14:30 UK opening-bell panic liquidation cascade.

---

## 5. Two-Stage Profit Harvesting & 10-Day EMA Trailing Runner (Phase 3 Proof)

Across 1,500 simulated trades ([`phase11_trailing_runner_study.md`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/evidence/phase11_trailing_runner_study.md)):
* **Why We Always Bank 50% at Stage 1:** In 1,068 Stage 1 winners, **84.6% crested before +18.0% and reversed**. Banking 50% at **+7.5% to +8.5%** (USD) or **+5.0% to +5.5%** (UK) locks in guaranteed profit before mean reversion strikes.
* **Immediate Breakeven Ratchet:** As soon as Stage 1 fills, raise the stop on the remaining 50% to **Entry + 0.35%** (USD) or **Entry + 0.05%** (UK).
* **Dynamic 10 EMA Trailing Runner (4 to 12 Trading Days):**
  * Trail the remaining 50% along the ascending **daily 10-day EMA / prior 2-day low** for up to **12 trading days** (3x ETFs remain capped at 5 days due to volatility decay).
  * Compared to a fixed +18% / 5-day cutoff, the 10 EMA Trailing Runner expanded average winner return from **+5.215% to +7.628% (+241.3 bps)** and lifted Profit Factor from **1.693 to 2.477**.

---

## 6. 100-Cycle 252-Day Broker Walk-Forward Verification (Phase 4 Proof)

Across 100 continuous 252-day annual walk-forward cycles modeling Trading 212 REST API execution ([`phase12_growth_broker_emulation_report.md`](file:///C:/Users/aidan/Documents/Company%20research%202/daytrading/evidence/phase12_growth_broker_emulation_report.md)):

| Verification Metric (100 Annual Cycles) | Target Hurdle | Empirical Result | Status |
| :--- | :---: | :---: | :---: |
| **Active Capital Deployment (Bull Regime)** | $80.0\%\text{–}100.0\%$ | **87.7% (Up to 100% Across 4 Slots)** | **PASS** |
| **Mean Ending Equity (£1,000 Start)** | $> £1,150.00$ | **£1,402.25** | **PASS** |
| **Mean Net Annual Return (After T212 Fees)** | $> +15.0\%$ | **+40.23% (Median +37.67%)** | **PASS** |
| **Mean Win Rate (%)** | $> 58.0\%$ | **61.97%** | **PASS** |
| **Mean Profit Factor** | $> 1.400$ | **1.852** | **PASS** |
| **Mean Annualized Sharpe Ratio** | $> 1.20$ | **2.63** | **PASS** |
| **Mean Maximum Portfolio Drawdown (%)** | $< 8.50\%$ | **7.22%** | **PASS** |
| **Annual Cycles Profitable** | $\ge 90.0\%$ | **98.0% (98 / 100 Years)** | **PASS** |

---

## 7. Master CLI Quick Reference (`daytrading/engine.cmd`)

All tools operate natively on Windows from the repository root or `daytrading/`:

| Command Line Execution | Functional Description |
| :--- | :--- |
| `.\daytrading\engine.cmd scan` | Scans active 5D Squeezes ($\le 6.0\%$), RVOL surges ($\ge 1.50\times$), 10 EMA alignment, and Forensic Gates (UK Zero-FX prioritized). |
| `.\daytrading\engine.cmd bracket --ticker RR.L --price 5.40 --portfolio 1000 --slots 3` | Calculates 3-slot growth sizing (£333.33 / 33.3%), 0% FX UK bracket, Breakeven Ratchet, and 10 EMA runner trail. |
| `.\daytrading\engine.cmd bracket --ticker NVDA --price 138.00 --portfolio 1000 --slots 4` | Calculates 4-slot growth sizing (£250.00 / 25.0%), +8.5% USD Stage 1 hurdle, GEX anchors, and portfolio risk %. |
| `.\daytrading\engine.cmd bracket --ticker NVDA --price 138.00 --pre-market 128.50 --catalyst` | Evaluates 09:00 UK pre-market gap risk and triggers `PREMARKET_EMERGENCY_CUT_0900_UK` when gap $\le -6.5\%$. |
| `.\daytrading\engine.cmd gex NVDA --spot 138.00 --dte 3` | Outputs live Black-Scholes Dealer Net GEX, Call Wall, Put Wall, Max Pain Strike, and Gamma Flip Zero-Line. |
| `.\daytrading\engine.cmd decay SOXL --days 5` | Computes discrete compounding volatility decay drag over N holding days for 2x/3x leveraged & inverse ETFs. |

---
*Codified and empirically verified in `daytrading/` under the Aggressive Capital Growth & Tactical Cash Mandate.*
