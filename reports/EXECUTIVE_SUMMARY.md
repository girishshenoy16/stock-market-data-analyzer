# Executive Summary: Indian Equity Markets Performance & Risk Intelligence (2021–2026)

**Target Asset Universe:** Reliance Industries (`RELIANCE.NS`), Tata Consultancy Services (`TCS.NS`), Infosys (`INFY.NS`), State Bank of India (`SBIN.NS`), ICICI Bank (`ICICIBANK.NS`), and the NIFTY 50 Benchmark Index (`^NSEI`).  
**Observation Window:** 28 September 2021 to 25 September 2026 (5-Year Calendar Horizon, 1,239 Trading Return Intervals).  
**Risk-Free Rate Proxy:** 10-Year Indian Government Security (G-Sec) Benchmark at 6.50% per annum ($R_{f,\text{daily}} = (1 + 0.065)^{1/252} - 1 = 0.025001\%$).  
**Methodology Version:** 2026.1 | **Pipeline Architecture:** Modular Python Analytics Engine with Single Source of Truth Lineage.

---

## 1. C-Suite Strategic Overview

Over the five-year investment cycle from September 2021 to September 2026, the Indian equity landscape exhibited profound divergence across macroeconomic sectors. While the broad market benchmark **NIFTY 50 (`^NSEI`)** generated a steady, low-volatility annualized return (**+5.46% CAGR** with **13.81% volatility**), the underlying individual equities traversed markedly disparate capital return and drawdown regimes.

The cycle was decisively characterized by:
1. **Banking Sector Hegemony:** Both public and private banking titans demonstrated unprecedented earnings expansion, asset quality cleanup, and credit growth, establishing themselves as the dominant engines of positive risk-adjusted alpha.
2. **IT Services Multiple Contraction:** Following historic post-pandemic valuations in late 2021, India's leading digital exporters faced severe valuation derating, global enterprise discretionary IT budget compression, and macroeconomic headwinds in North American and European markets.
3. **Conglomerate Rangebound Consolidation:** Energy and telecom conglomerate Reliance Industries delivered modest positive compounding (+1.22% CAGR) but failed to surmount the 6.50% domestic risk-free hurdle, resulting in negative risk-adjusted excess returns.
4. **Diversification Superiority:** The 50-stock benchmark delivered the highest risk-adjusted capital preservation, experiencing only a **-17.23% maximum drawdown** versus **-22.33% to -53.39%** for individual corporate equities.

---

## 2. Master Performance & Risk Scorecard

The following authoritative metrics are derived directly from the single source of truth engineered dataset (`data/processed/market_summary_metrics.csv`):

| Instrument | Last Close | 5-Yr CAGR | Ann. Volatility | Sharpe Ratio ($R_f=6.5\%$) | Max Drawdown | Historical VaR (95%) | Beta vs NIFTY | 52W Range Position |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NIFTY 50 (`^NSEI`)** *(Benchmark)* | **23,140.50 pts** | **+5.46%** | **13.81%** | **+0.01** | **-17.23%** | **-1.39%** | **1.00** | 22.9% |
| **State Bank of India (`SBIN.NS`)** | ₹983.00 | **+19.33%** | 24.51% | **+0.60** | -23.94% | -2.21% | 1.16 | 38.7% |
| **ICICI Bank Limited (`ICICIBANK.NS`)** | ₹1,326.80 | **+14.00%** | 20.15% | **+0.45** | -22.33% | -1.85% | 0.97 | 51.4% |
| **Reliance Industries (`RELIANCE.NS`)** | ₹1,226.00 | **+1.22%** | 22.28% | **-0.12** | -27.18% | -2.13% | 1.11 | 3.9% |
| **Infosys Limited (`INFY.NS`)** | ₹1,000.20 | **-7.42%** | 25.96% | **-0.41** | -48.17% | -2.61% | 0.97 | 2.5% |
| **TCS Limited (`TCS.NS`)** | ₹2,082.00 | **-8.72%** | 22.58% | **-0.58** | -53.39% | -2.11% | 0.81 | 8.8% |

---

## 3. Objective Empirical Rankings

### A. Annualized Capital Compounding (5-Year CAGR)
1. **State Bank of India (`SBIN.NS`):** **+19.33% p.a.** — *Sector-leading balance sheet recovery and sustained credit growth.*
2. **ICICI Bank Limited (`ICICIBANK.NS`):** **+14.00% p.a.** — *Consistently high net interest margins (NIMs) and best-in-class ROA.*
3. **NIFTY 50 (`^NSEI`):** **+5.46% p.a.** — *Market benchmark anchor providing broad multi-sector representation.*
4. **Reliance Industries (`RELIANCE.NS`):** **+1.22% p.a.** — *Capital reinvestment cycle in retail and 5G telecommunications.*
5. **Infosys Limited (`INFY.NS`):** **-7.42% p.a.** — *Valuation multiple compression from peak 2021 pandemic multiples.*
6. **TCS Limited (`TCS.NS`):** **-8.72% p.a.** — *Prolonged margin stagnation and enterprise IT spending rationalization.*

### B. Risk-Adjusted Efficiency (Sharpe Ratio with 6.50% Risk-Free Rate)
1. **State Bank of India (`SBIN.NS`):** **+0.60** — *Strongest reward-to-volatility ratio across the target universe.*
2. **ICICI Bank Limited (`ICICIBANK.NS`):** **+0.45** — *Exceptional risk-adjusted excess returns above G-Sec hurdle.*
3. **NIFTY 50 (`^NSEI`):** **+0.01** — *Virtually identical to the 10-Yr Indian G-Sec return over the 5-year cycle.*
4. **Reliance Industries (`RELIANCE.NS`):** **-0.12** — *Underperformed the risk-free rate; equity risk premium was negative.*
5. **Infosys Limited (`INFY.NS`):** **-0.41** — *Negative excess returns combined with top-tier volatility (25.96%).*
6. **TCS Limited (`TCS.NS`):** **-0.58** — *Lowest risk-adjusted performance due to sustained negative compounding.*

### C. Volatility & Tail Risk Protection (Annualized Standard Deviation & VaR 95%)
- **Lowest Return Volatility:** **NIFTY 50 (13.81%)** $\ll$ ICICI Bank (20.15%) $\approx$ Reliance (22.28%) $\approx$ TCS (22.58%) $\approx$ SBI (24.51%) $\approx$ Infosys (25.96%).
- **Strongest Daily Tail Preservation (VaR 95%):** **NIFTY 50 (-1.39%)**, followed by ICICIBANK (-1.85%), TCS (-2.11%), RELIANCE (-2.13%), SBIN (-2.21%), and INFY (-2.61%).

### D. Downside Capital Preservation (Maximum Drawdown)
- **Top Capital Preservation:** **NIFTY 50 (-17.23%)** restricted peak retracement through index constituent rebalancing.
- **Moderate Drawdown Regime:** **ICICIBANK (-22.33%)**, **SBIN (-23.94%)**, and **RELIANCE (-27.18%)**.
- **Severe Retracement Regime:** **INFY (-48.17%)** and **TCS (-53.39%)** lost approximately half their peak capitalization during the tech valuation contraction of 2022–2023.

---

## 4. Sector-by-Sector In-Depth Analysis

### A. The Banking Renaissance: Public vs. Private Outperformance
The banking sector was the undisputed outperformer of the Indian financial markets over the 2021–2026 cycle. 

- **State Bank of India (`SBIN.NS`):** 
  - Achieved a stellar **+19.33% CAGR**, turning a ₹100 investment in September 2021 into ₹241.54 by September 2026.
  - Benefited from systemic NPA resolution, elevated net interest margins during the RBI's repo rate tightening cycle (6.50%), and massive corporate lending demand.
  - Despite registering higher annualized volatility (24.51%) and a high beta (1.16), its excess return was sufficient to yield the universe's highest Sharpe ratio (+0.60).
- **ICICI Bank Limited (`ICICIBANK.NS`):**
  - Compounded at **+14.00% CAGR** with a more subdued volatility profile (**20.15%**) and the lowest drawdown among all single equities (**-22.33%**).
  - Its beta of **0.97** reflects equity defensiveness coupled with private banking leadership, resulting in an institutional-grade Sharpe ratio of **+0.45**.

### B. Information Technology: The Post-Pandemic Contraction
In stark contrast to consensus institutional forecasts in 2021, the Indian IT services sector faced an extended period of valuation correction and revenue deceleration.

- **Valuation Starting Point Distortion:** In September 2021, both TCS and Infosys traded at historically elevated price-to-earnings multiples ($>35\times$) fueled by the global pandemic digital transformation wave.
- **Enterprise Expenditure Freezes:** As global central banks enacted aggressive rate hiking cycles in 2022–2023, Fortune 500 discretionary tech spending, BFSI software investments, and consulting engagements contracted sharply.
- **Comparative Mechanics:**
  - **TCS:** Compounded at **-8.72% CAGR**, experiencing a devastating **-53.39% maximum drawdown**. While maintaining a defensive beta (0.81), its return profile generated a Sharpe ratio of **-0.58**.
  - **Infosys:** Compounded at **-7.42% CAGR** with the highest volatility in the entire universe (**25.96%**) and a **-48.17% maximum drawdown**.
  - **52-Week Range Status:** As of September 2026, both TCS (8.8%) and Infosys (2.5%) are trading near the bottom of their 52-week trading corridors, reflecting continued market caution.

### C. Industrial & Consumer Conglomerate: Reliance Industries
- Reliance Industries (`RELIANCE.NS`) generated a positive **+1.22% CAGR**, moving from an adjusted base of ₹1,154.06 in September 2021 to ₹1,226.00 in September 2026.
- The company engaged in massive capital expenditure programs across its 5G telecommunications roll-out, retail network expansion, and new energy gigafactories.
- With an annualized volatility of **22.28%** and a beta of **1.11**, Reliance's return lagged the domestic risk-free rate hurdle of 6.50%, generating an annualized Sharpe ratio of **-0.12** and trading at just 3.9% of its 52-week corridor as of late September 2026.

### D. Benchmark Index Dynamics: NIFTY 50
- The NIFTY 50 index delivered a **+5.46% CAGR**, moving from 17,748.60 pts to 23,140.50 pts.
- **The Case for Passive Indexing:** The benchmark's Sharpe ratio (+0.01) matches the 10-Yr G-Sec proxy while cutting volatility in half compared to individual stocks (13.81% vs. 20.15%–25.96%).
- Index diversification completely shielded institutional investors from the catastrophic 50%+ drawdowns suffered by standalone equity leaders like TCS and Infosys.

---

## 5. Strategic Investment Takeaways for Portfolio Allocators

1. **Sector Diversification Is Non-Negotiable:** A concentrated allocation to premier Indian IT giants in September 2021 would have destroyed nearly 40% of investor capital over 5 years. Conversely, a balanced portfolio pairing IT with Banking captured alpha while mitigating sector-specific cyclical shocks.
2. **PSU Banks Re-Rated Structurally:** SBIN proved that structural balance sheet reform can transform a traditionally discounted public enterprise into the premier wealth-generating instrument in Indian capital markets.
3. **The Power of Index Capital Preservation:** The benchmark's max drawdown was capped at -17.23%, underscoring the critical risk-dampening mechanics of market-cap-weighted index rebalancing during idiosyncratic corporate downturns.
4. **Current Corridor Asymmetry (Late 2026):** With INFY (2.5%), RELIANCE (3.9%), and TCS (8.8%) compressed near their 52-week lows, while ICICIBANK (51.4%) and SBIN (38.7%) trade near midpoint to highs, risk-reward skew heading into the subsequent cycle favors mean-reversion assessments in oversold quality blue-chips.

---

*Educational Disclaimer: This executive summary was generated from empirical quantitative analytics for academic and demonstration purposes. It does not constitute investment advice or a recommendation to purchase or sell any security.*
