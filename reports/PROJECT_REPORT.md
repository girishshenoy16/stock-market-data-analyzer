# Technical Project Report: Quantitative Financial Analytics Pipeline & Executive Web Intelligence Engine

**Project Title:** Stock Market Data Analyzer — Indian Equity Markets & Benchmark Index (2021–2026)  
**Curriculum Track:** Diploma in Financial Engineering & Quantitative Analytics  
**Author:** Antigravity Autonomous Engineering Agent  
**Supervisor / Mentor:** Umesh Yadav Sir  
**Observation Window:** 28 September 2021 to 28 September 2026 (Historical Data: 28 September 2021 to 25 September 2026)  
**Methodology Version:** 2026.1 | **Schema Version:** 1.0.0  
**Repository Architecture:** Static GitHub Pages Deployment (`docs/`) backed by Modular Python Data Lineage Pipeline  

---

## Table of Contents

1. [Executive Synopsis & Project Governance](#1-executive-synopsis--project-governance)
2. [Target Asset Universe & Instrument Specifications](#2-target-asset-universe--instrument-specifications)
3. [System Architecture & 8-Stage Data Lineage Pipeline](#3-system-architecture--8-stage-data-lineage-pipeline)
4. [Data Quality Engineering & Trading Calendar Normalization](#4-data-quality-engineering--trading-calendar-normalization)
5. [Mathematical Formulations & Quantitative Finance Foundations](#5-mathematical-formulations--quantitative-finance-foundations)
   - 5.1 Compounded Annual Growth Rate (CAGR)
   - 5.2 Compounded Daily Risk-Free Rate Conversion
   - 5.3 Annualized Sample Volatility
   - 5.4 Annualized Sharpe Ratio
   - 5.5 Systematic Risk (Beta vs. Benchmark)
   - 5.6 Joint Inner-Join Pearson Correlation Matrix
   - 5.7 Wilder's 14-Day Relative Strength Index (RSI-14)
   - 5.8 Bollinger Bands Envelopment
   - 5.9 Trend Averages & Regime Crossover Signals
   - 5.10 Drawdown Series & Maximum Drawdown (MDD)
   - 5.11 Adjusted Rolling 52-Week High and Low Corridor
   - 5.12 Historical Value at Risk (VaR 95%)
6. [Complete Data Dictionary & Schema Specifications](#6-complete-data-dictionary--schema-specifications)
7. [Comprehensive Empirical Findings & Asset-by-Asset Quantitative Dossier](#7-comprehensive-empirical-findings--asset-by-asset-quantitative-dossier)
8. [Cross-Asset Correlation, Diversification & Beta Dynamics](#8-cross-asset-correlation-diversification--beta-dynamics)
9. [Web Dashboard Architecture & Client Presentation Layer](#9-web-dashboard-architecture--client-presentation-layer)
10. [Quality Assurance, Automated Testing & Verification Suite](#10-quality-assurance-automated-testing--verification-suite)
11. [Assumptions, Proxy Limitations & Educational Disclaimer](#11-assumptions-proxy-limitations--educational-disclaimer)

---

## 1. Executive Synopsis & Project Governance

The **Stock Market Data Analyzer** is an enterprise-grade, reproducible financial engineering system engineered to analyze the historical dynamics, return distributions, volatility profiles, and tail risks of blue-chip Indian equities alongside the National Stock Exchange benchmark (**NIFTY 50**). Spanning a precise 5-year calendar horizon from 28 September 2021 to 28 September 2026 (yielding 1,239 return intervals across 1,240 trading sessions), the system bridges institutional quantitative modeling with modern corporate web presentation.

### Core Governance Principles
1. **Single Source of Truth Lineage:** All downstream artifacts—including publication-grade static figures, automated performance digests, and the interactive web application—are strictly derived from deterministic, immutable Python feature-engineered CSV files.
2. **Zero Client-Side Statistical Recalculation:** The client web dashboard functions as a pure presentation layer. All indicators, period returns, drawdowns, Sharpe ratios, and correlation matrices are precalculated in Python and bundled into a versioned data schema (`docs/dashboard_data.js`). The browser performs zero floating-point quantitative modeling.
3. **Price Basis Consistency:** Corporate actions (stock splits, bonus issues, and capital adjustments) frequently introduce artificial price cliffs in unadjusted price series. The system mandates an **effective adjusted-price basis** for all return calculations, technical overlays, moving averages, Bollinger Bands, and rolling corridors, while proportionally scaling open, high, and low values to guarantee visual and mathematical integrity.
4. **Reproducible Hermetic Testing:** Testing is partitioned into a 100% offline, hermetic suite utilizing synthetic mock fixtures (ensuring CI/CD pipelines run without network dependencies) and an isolated live network test suite explicitly requiring active API credentials.

---

## 2. Target Asset Universe & Instrument Specifications

The target universe captures key sectors representing the core capital engines of the Indian economy:

| Ticker | Corporate Entity | Primary Sector | Exchange | Weight / Role |
| :--- | :--- | :--- | :--- | :--- |
| **`^NSEI`** | **NIFTY 50 Benchmark Index** | Broad Market Benchmark | NSE | National market proxy comprising 50 blue-chip leaders. |
| **`RELIANCE.NS`** | **Reliance Industries Limited** | Energy, Retail, Digital Services | NSE | Largest conglomerate by market capitalization in India. |
| **`TCS.NS`** | **Tata Consultancy Services Limited** | Information Technology Services | NSE | Premier global IT services exporter and market bellwether. |
| **`INFY.NS`** | **Infosys Limited** | Information Technology Services | NSE | Leading enterprise digital software and consulting provider. |
| **`SBIN.NS`** | **State Bank of India** | Public Sector Banking | NSE | Dominant public commercial banking and credit institution. |
| **`ICICIBANK.NS`** | **ICICI Bank Limited** | Private Sector Banking | NSE | Premier private banking powerhouse with extensive retail footprint. |

---

## 3. System Architecture & 8-Stage Data Lineage Pipeline

The system is constructed as a strictly linear, stage-gated architecture. If any stage encounters a schema violation, data corruption, or execution failure, the orchestrator immediately terminates the pipeline with a non-zero exit code to prevent contaminated data propagation.

```
+---------------------------------------------------------------------------------------+
|                              MASTER PIPELINE ARCHITECTURE                             |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
[Stage 1: Ingestion & Archival] ────────► Download 5Y daily data via yfinance (auto_adjust=False)
  (src/data_loader.py)                    Save immutable raw snapshot to data/raw/{TICKER}_raw.csv
                                           Archive timestamped copy to data/raw/archive/
                                           |
                                           v
[Stage 2: Cleaning & Validation] ───────► Enforce trading calendar integrity (no blind fills)
  (src/cleaner.py)                        Validate Close > 0; reject corrupted session records
                                           Calculate adjustment factor f_t = Adj_Close / Close
                                           Generate proportionally adjusted OHLC (adj_open, etc.)
                                           Output: data/processed/{TICKER}_cleaned.csv
                                           |
                                           v
[Stage 3: Exploratory Data Analysis] ───► Generate 5 300-DPI visual diagnostics:
  (src/eda.py)                            Outputs saved to outputs/eda/*.png
                                           |
                                           v
[Stage 4: Feature Engineering] ─────────► Returns, Volatility (ddof=1), Sharpe (Rf=6.5% p.a.),
  (src/feature_engineering.py)            Rolling 52W High/Low (252-day window, 251 NaN warm-up),
                                           Wilder's RSI-14 (zero-gain/loss safeguards), Bollinger Bands,
                                           Pairwise Beta vs. NIFTY 50, Joint inner-join Correlation.
                                           Outputs: data/processed/{TICKER}_engineered.csv
                                                    data/processed/market_summary_metrics.csv
                                           |
                                           v
[Stage 5: Static Visualizations] ───────► Generate 18 publication-ready 300-DPI PNG charts:
  (src/visualizer.py)                     Outputs saved to outputs/charts/*.png
                                           |
                                           v
[Stage 6: Web Dashboard Exporter] ──────► Compile engineered data + summary metrics into:
  (src/dashboard_exporter.py)              docs/dashboard_data.js (Versioned JS Schema v1.0.0)
                                           Includes multi-period precomputations (5Y, 3Y, 1Y, YTD)
                                           |
                                           v
[Stage 7: Automated Reporting] ─────────► Generate automated text performance digest:
  (src/reporter.py)                        outputs/reports/automated_performance_digest.txt
                                           Author reports/EXECUTIVE_SUMMARY.md & PROJECT_REPORT.md
                                           |
                                           v
[Stage 8: Client Web Presentation] ─────► Interactive Static GitHub Pages Dashboard:
  (docs/index.html, app.js, style.css)     PowerBI theme, benchmark pinned, 100% client-side render
```

---

## 4. Data Quality Engineering & Trading Calendar Normalization

### 4.1 Strict Missing Data Policy & Rejection of Blind Imputation
In quantitative time-series modeling, forward-filling (`ffill`) or backward-filling (`bfill`) missing price records across market holidays or weekends corrupts calendar volatility estimates, artificially deflates standard deviations, and fabricates zero-return days that distort kurtosis.
- **Trading Calendar Preservation:** The pipeline strictly preserves authentic exchange trading sessions. No weekend or holiday synthetic records are inserted.
- **Rejection Policy:** Any raw market record where `Close` is missing, NaN, non-finite, or $\le 0$ indicates data vendor corruption. Such records are discarded during the cleaning phase (`src/cleaner.py`), and the rejection is logged in `outputs/reports/data_cleaning_audit.json`.

### 4.2 Proportional OHLC Scaling & Fallback Mechanics
Unadjusted `Open`, `High`, and `Low` series cannot be compared directly against `Adj Close` without creating false candlestick wicks and artificial chart distortions across corporate action dates. The pipeline applies a proportional adjustment factor:

$$f_t = \frac{\text{Adj Close}_t}{\text{Close}_t}$$

$$\text{Adj Open}_t = \text{Open}_t \times f_t, \quad \text{Adj High}_t = \text{High}_t \times f_t, \quad \text{Adj Low}_t = \text{Low}_t \times f_t, \quad \text{Adj Close}_t = \text{Close}_t \times f_t$$

- **Corrupted Factor Safeguard:** If $\text{Adj Close}_t$ is missing or non-positive, the pipeline sets $f_t = 1.0$, falls back to raw prices, and issues an explicit warning log.
- **Preservation of Raw Values:** Unadjusted raw `open`, `high`, `low`, `close`, and `volume` fields are preserved in all cleaned and engineered CSVs for statutory auditability.

---

## 5. Mathematical Formulations & Quantitative Finance Foundations

### 5.1 Compounded Annual Growth Rate (CAGR)
CAGR evaluates the constant geometric annual growth rate required for an investment to grow from its initial value to its terminal value over the exact calendar duration.

$$\text{CAGR} = \left( \frac{P_{\text{end}}}{P_{\text{start}}} \right)^{\frac{1}{\text{calendar\_duration\_years}}} - 1$$

Where:
$$\text{calendar\_duration\_years} = \frac{\text{Calendar Days Between } P_{\text{start}} \text{ and } P_{\text{end}}}{365.25}$$

*Implementation Detail:* For the observation window (28 September 2021 to 25 September 2026), $\text{calendar\_duration\_years} = \frac{1823}{365.25} = 4.991102\text{ years}$. The number of discrete return intervals ($N = 1,239$) is preserved in metadata.

### 5.2 Compounded Daily Risk-Free Rate Conversion
The project assumes an illustrative domestic benchmark risk-free rate of **6.50% per annum**, representing the yield of the 10-Year Indian Government Security (G-Sec). To avoid compounding distortion, the annual rate is converted to an exact daily compounded rate assuming 252 annual trading sessions:

$$R_{f,\text{daily}} = (1 + R_{f,\text{annual}})^{\frac{1}{252}} - 1 = (1 + 0.065)^{\frac{1}{252}} - 1 \approx 0.000250007 \quad (0.025001\% \text{ per day})$$

### 5.3 Annualized Sample Volatility
Daily arithmetic returns are defined as:

$$R_t = \frac{\text{Adj Close}_t - \text{Adj Close}_{t-1}}{\text{Adj Close}_{t-1}}$$

Sample volatility is computed with Bessel's correction ($\text{ddof} = 1$) to yield an unbiased estimator:

$$\sigma_{\text{daily}} = \sqrt{\frac{1}{N - 1} \sum_{t=1}^{N} (R_t - \bar{R})^2}$$

Annualized volatility scales by the square root of 252 trading days:

$$\sigma_{\text{annual}} = \sigma_{\text{daily}} \times \sqrt{252}$$

### 5.4 Annualized Sharpe Ratio
The Sharpe ratio measures excess return per unit of total risk. To guarantee mathematical precision, the mean daily excess return is annualized using the 252-factor:

$$\text{Sharpe Ratio} = \sqrt{252} \times \frac{\frac{1}{N} \sum_{t=1}^{N} (R_t - R_{f,\text{daily}})}{\sqrt{\frac{1}{N - 1} \sum_{t=1}^{N} (R_t - R_{f,\text{daily}} - \overline{R_{\text{excess}}})^2}}$$

### 5.5 Systematic Risk (Beta vs. Benchmark)
Beta measures the sensitivity of an equity's returns relative to the movements of the NIFTY 50 benchmark index:

$$\beta_i = \frac{\text{Cov}(R_i, R_{\text{benchmark}})}{\text{Var}(R_{\text{benchmark}})} = \frac{\sum (R_{i,t} - \bar{R}_i)(R_{m,t} - \bar{R}_m)}{\sum (R_{m,t} - \bar{R}_m)^2}$$

*Data Alignment Mandate:* Beta is calculated exclusively on **pairwise date-aligned returns** (inner join on `Date` between the stock and `^NSEI`). A minimum observation threshold ($N \ge 30$) and non-zero benchmark variance check ($\text{Var}(R_m) > 0$) are enforced.

### 5.6 Joint Inner-Join Pearson Correlation Matrix
Pairwise correlation across all six assets is calculated exclusively on the **joint date-aligned complete-case matrix** (filtering for dates where all 6 instruments traded simultaneously, yielding 1,234 joint observations):

$$\rho_{i,j} = \frac{\sum_{t=1}^{M} (R_{i,t} - \bar{R}_i)(R_{j,t} - \bar{R}_j)}{\sqrt{\sum_{t=1}^{M} (R_{i,t} - \bar{R}_i)^2 \sum_{t=1}^{M} (R_{j,t} - \bar{R}_j)^2}}$$

The resulting $6 \times 6$ matrix is mathematically symmetric and positive semi-definite subject to floating-point numerical tolerances.

### 5.7 Wilder's 14-Day Relative Strength Index (RSI-14)
RSI-14 utilizes J. Welles Wilder's Exponential Smoothing technique ($\alpha = 1/14$).

1. Define upward changes $U_t = \max(R_{\text{price}, t}, 0)$ and downward changes $D_t = \max(-R_{\text{price}, t}, 0)$.
2. Initial 14-day simple moving averages:
   $$\text{Avg Gain}_0 = \frac{1}{14} \sum_{i=1}^{14} U_i, \quad \text{Avg Loss}_0 = \frac{1}{14} \sum_{i=1}^{14} D_i$$
3. Subsequent Wilder smoothing:
   $$\text{Avg Gain}_t = \frac{\text{Avg Gain}_{t-1} \times 13 + U_t}{14}, \quad \text{Avg Loss}_t = \frac{\text{Avg Loss}_{t-1} \times 13 + D_t}{14}$$
4. Relative Strength & Safeguards:
   $$RS_t = \frac{\text{Avg Gain}_t}{\text{Avg Loss}_t}$$
   $$\text{RSI}_t = 100 - \frac{100}{1 + RS_t}$$
   - **Zero Loss Edge Case:** If $\text{Avg Loss} = 0$ and $\text{Avg Gain} > 0$, $\text{RSI} = 100.0$.
   - **Zero Gain & Loss Edge Case:** If $\text{Avg Gain} = 0$ and $\text{Avg Loss} = 0$, $\text{RSI} = 50.0$.
   - **Zero Gain Edge Case:** If $\text{Avg Gain} = 0$ and $\text{Avg Loss} > 0$, $\text{RSI} = 0.0$.

### 5.8 Bollinger Bands Envelopment
Computed using a 20-day rolling window on effective adjusted close prices:

$$\text{Middle Band}_t = \text{SMA}_{20}(P_t) = \frac{1}{20} \sum_{k=0}^{19} P_{t-k}$$

$$\sigma_{20, t} = \sqrt{\frac{1}{19} \sum_{k=0}^{19} (P_{t-k} - \text{SMA}_{20}(P_t))^2}$$

$$\text{Upper Band}_t = \text{Middle Band}_t + (2 \times \sigma_{20, t}), \quad \text{Lower Band}_t = \text{Middle Band}_t - (2 \times \sigma_{20, t})$$

### 5.9 Trend Moving Averages & Regime Crossover Signals
- **Simple Moving Averages:** $\text{SMA}_k(P_t) = \frac{1}{k} \sum_{i=0}^{k-1} P_{t-i}$ for $k \in \{20, 50, 200\}$.
- **Exponential Moving Average:** $\text{EMA}_{20}(P_t) = \alpha P_t + (1 - \alpha) \text{EMA}_{20}(P_{t-1})$ where $\alpha = \frac{2}{20 + 1} \approx 0.095238$.
- **Golden Cross Event:** A discrete impulse flag ($= 1$ strictly on the session where $\text{SMA}_{50, t} > \text{SMA}_{200, t}$ and $\text{SMA}_{50, t-1} \le \text{SMA}_{200, t-1}$; 0 otherwise).
- **Death Cross Event:** A discrete impulse flag ($= 1$ strictly on the session where $\text{SMA}_{50, t} < \text{SMA}_{200, t}$ and $\text{SMA}_{50, t-1} \ge \text{SMA}_{200, t-1}$; 0 otherwise).
- **Bullish Regime Indicator:** A continuous state variable ($= 1$ whenever $\text{SMA}_{50, t} > \text{SMA}_{200, t}$; 0 otherwise).

### 5.10 Drawdown Series & Maximum Drawdown (MDD)
Drawdown measures the percentage decline from the historical cumulative peak:

$$\text{Peak}_t = \max_{k \le t} (\text{Adj Close}_k)$$

$$\text{Drawdown}_t = \frac{\text{Adj Close}_t - \text{Peak}_t}{\text{Peak}_t}$$

$$\text{Maximum Drawdown} = \min_{t} (\text{Drawdown}_t)$$

### 5.11 Adjusted Rolling 52-Week High and Low Corridor
The 52-week corridor evaluates the price range across a rolling 252-trading-session window on the adjusted price basis:

$$\text{Rolling 52W High}_t = \max_{k=0}^{251} (\text{Adj High}_{t-k})$$

$$\text{Rolling 52W Low}_t = \min_{k=0}^{251} (\text{Adj Low}_{t-k})$$

*Warm-Up Mandate:* `min_periods = 252` is strictly enforced. The first 251 observations are evaluated as `NaN` (no expanding window fallback). Valid values commence strictly on observation 252.

### 5.12 Historical Value at Risk (VaR 95%)
Historical 1-day Value at Risk at the 95% confidence level is the non-parametric 5th percentile of the daily return distribution:

$$\text{VaR}_{95\%} = \text{Percentile}(R, 5.0)$$

---

## 6. Complete Data Dictionary & Schema Specifications

### 6.1 Cleaned Data Schema (`data/processed/{TICKER}_cleaned.csv`)
- `Date` *(string, YYYY-MM-DD)*: Exchange trading session date.
- `open`, `high`, `low`, `close` *(float)*: Unadjusted raw prices from Yahoo Finance.
- `adj_close` *(float)*: Corporate-action-adjusted closing price.
- `volume` *(integer)*: Traded session share volume.
- `adjustment_factor` *(float)*: Proportional adjustment factor $f_t = \text{adj\_close} / \text{close}$.
- `adj_open`, `adj_high`, `adj_low` *(float)*: Proportionally adjusted OHLC series.

### 6.2 Engineered Data Schema (`data/processed/{TICKER}_engineered.csv`)
Contains all cleaned columns plus 26 engineered quantitative features:
- `daily_return`, `log_return`, `cumulative_return`: Return series.
- `normalized_price`: Wealth trajectory indexed to 100.0 from own first valid date ($P_t / P_0 \times 100$).
- `sma_20`, `sma_50`, `sma_200`, `ema_20`: Moving average ribbons.
- `bb_upper`, `bb_middle`, `bb_lower`: Bollinger Bands series.
- `rsi_14`: 14-day Wilder RSI.
- `running_peak`, `drawdown`: Historical peak price and underwater drawdown series.
- `rolling_vol_30d`: 30-day annualized rolling volatility ($\text{ddof}=1$).
- `golden_cross_event`, `death_cross_event`: Discrete crossover markers.
- `bullish_regime`: Continuous moving average regime flag.
- `rolling_52w_high`, `rolling_52w_low`: 252-day adjusted high and low corridors.
- `volume_sma_20`: 20-day moving average of share volume.
- `volume_spike_ratio`: Volume divided by `volume_sma_20`.

### 6.3 Master Summary Schema (`data/processed/market_summary_metrics.csv`)
Summary record containing 12 columns per instrument:
- `ticker`: Symbol identifier.
- `cagr_pct`: 5-year annualized CAGR (%).
- `annualized_volatility_pct`: Full-period annualized volatility (%).
- `sharpe_ratio`: Annualized Sharpe ratio ($R_f = 6.50\%$).
- `max_drawdown_pct`: Full-period maximum drawdown (%).
- `var_95_pct`: 1-day 95% historical Value at Risk (%).
- `beta_nifty`: Beta relative to NIFTY 50.
- `last_close`: Most recent trading session close price.
- `52w_high`, `52w_low`: Latest rolling 52-week adjusted bounds.
- `trading_return_intervals`: Count of return intervals (1,239 for equities; 1,234 for index).
- `calendar_duration_years`: Exact duration exponent ($4.9911\text{ years}$).

---

## 7. Comprehensive Empirical Findings & Asset-by-Asset Quantitative Dossier

Below is the verified performance and risk breakdown across all six instruments over the 5-year cycle:

```
+========================================================================================================+
|                              EMPIRICAL PERFORMANCE SUMMARY (2021–2026)                                 |
+========================================================================================================+
| Instrument    | Last Close     | 5-Yr CAGR | Ann. Vol | Sharpe (6.5%) | Max DD   | VaR 95% | Beta vs NIFTY |
+---------------+----------------+-----------+----------+---------------+----------+---------+---------------+
| ^NSEI (Bench) | 23,140.50 pts  |  +5.46%   |  13.81%  |     +0.01     | -17.23%  | -1.39%  |     1.00      |
| SBIN.NS       | ₹983.00        | +19.33%   |  24.51%  |     +0.60     | -23.94%  | -2.21%  |     1.16      |
| ICICIBANK.NS  | ₹1,326.80      | +14.00%   |  20.15%  |     +0.45     | -22.33%  | -1.85%  |     0.97      |
| RELIANCE.NS   | ₹1,226.00      |  +1.22%   |  22.28%  |     -0.12     | -27.18%  | -2.13%  |     1.11      |
| INFY.NS       | ₹1,000.20      |  -7.42%   |  25.96%  |     -0.41     | -48.17%  | -2.61%  |     0.97      |
| TCS.NS        | ₹2,082.00      |  -8.72%   |  22.58%  |     -0.58     | -53.39%  | -2.11%  |     0.81      |
+========================================================================================================+
```

### 7.1 State Bank of India (`SBIN.NS`) — The Alpha Powerhouse
- **Capital Trajectory:** Base price indexed at ₹406.97 on 28 September 2021; closed at ₹983.00 on 25 September 2026.
- **CAGR:** **+19.33%**, ranking #1 across the asset universe.
- **Risk Metrics:** Annualized volatility of **24.51%**, generating a top-tier Sharpe ratio of **+0.60**.
- **Drawdown:** Contained at **-23.94%**, remarkably shallow for a high-beta (1.16) cyclical PSU bank.
- **Synthesis:** SBIN underwent a historic structural balance sheet cleanup, benefiting from strong credit expansion and corporate profitability in the post-pandemic cycle.

### 7.2 ICICI Bank Limited (`ICICIBANK.NS`) — Private Sector Quality Compounder
- **Capital Trajectory:** Base price of ₹689.83; closed at ₹1,326.80.
- **CAGR:** **+14.00%**, ranking #2 in capital growth.
- **Risk Profile:** Volatility of **20.15%** (lowest among all single equities) and a max drawdown of **-22.33%**.
- **Sharpe Ratio:** **+0.45**, delivering institutional-grade risk-adjusted excess returns with a defensive beta of **0.97**.
- **Synthesis:** Demonstrates the defensive superiority of premier private banking franchises characterized by high net interest margins and prudent risk provisioning.

### 7.3 NIFTY 50 Benchmark Index (`^NSEI`) — The Diversification Shield
- **Capital Trajectory:** 17,748.60 pts to 23,140.50 pts (**+5.46% CAGR**).
- **Risk Metrics:** Annualized volatility was just **13.81%** (nearly half that of individual equities).
- **Capital Preservation:** Maximum drawdown was restricted to **-17.23%**, and 1-day 95% VaR was **-1.39%**, establishing the benchmark as the premier defensive asset against idiosyncratic corporate distress.
- **Sharpe Ratio:** **+0.01**, matching the 10-Yr G-Sec proxy over the 5-year cycle.

### 7.4 Reliance Industries Limited (`RELIANCE.NS`) — Conglomerate Capex Cycle
- **Capital Trajectory:** Base price ₹1,154.06; closed at ₹1,226.00 (**+1.22% CAGR**).
- **Risk Metrics:** Annualized volatility of **22.28%**, max drawdown of **-27.18%**, and beta of **1.11**.
- **Sharpe Ratio:** **-0.12**, reflecting that equity risk was uncompensated relative to the 6.50% domestic risk-free rate hurdle.
- **Synthesis:** Significant capital allocation to 5G infrastructure, retail store roll-outs, and renewable energy assets compressed free cash flow yield over the medium-term horizon.

### 7.5 Infosys Limited (`INFY.NS`) & TCS Limited (`TCS.NS`) — The Tech Winter
- **Capital Trajectory:** 
  - INFY fell from ₹1,469.42 to ₹1,000.20 (**-7.42% CAGR**).
  - TCS fell from ₹3,282.94 to ₹2,082.00 (**-8.72% CAGR**).
- **Drawdown Severity:** TCS suffered a peak-to-trough decline of **-53.39%**, and INFY declined **-48.17%**.
- **Risk Metrics:** INFY registered the highest volatility in the entire universe (**25.96%**), while TCS registered **22.58%**.
- **Sharpe Ratios:** Heavily negative at **-0.41** (INFY) and **-0.58** (TCS).
- **Synthesis:** High starting valuations in late 2021 combined with global macro interest rate shocks, tech budget cuts in banking and retail, and multiple derating caused severe capital erosion across tier-1 Indian digital exporters.

---

## 8. Cross-Asset Correlation, Diversification & Beta Dynamics

### 8.1 Joint Inner-Join Correlation Matrix
Computed on 1,234 joint trading dates across all six instruments:

```
+=======================================================================================+
|                            CROSS-ASSET CORRELATION MATRIX                             |
+=======================================================================================+
| Instrument    | RELIANCE.NS |   TCS.NS    |   INFY.NS   |   SBIN.NS   | ICICIBANK.NS| ^NSEI   |
+---------------+-------------+-------------+-------------+-------------+-------------+---------+
| RELIANCE.NS   |    1.0000   |    0.2681   |    0.2635   |    0.4326   |    0.3421   |  0.6868 |
| TCS.NS        |    0.2681   |    1.0000   |    0.7314   |    0.1912   |    0.2104   |  0.4982 |
| INFY.NS       |    0.2635   |    0.7314   |    1.0000   |    0.1789   |    0.2312   |  0.5186 |
| SBIN.NS       |    0.4326   |    0.1912   |    0.1789   |    1.0000   |    0.5098   |  0.6482 |
| ICICIBANK.NS  |    0.3421   |    0.2104   |    0.2312   |    0.5098   |    1.0000   |  0.6625 |
| ^NSEI         |    0.6868   |    0.4982   |    0.5186   |    0.6482   |    0.6625   |  1.0000 |
+=======================================================================================+
```

### 8.2 Analytical Diversification Insights
1. **Intra-Sector Clustering:** TCS and INFY exhibit a robust positive correlation of **0.7314**, confirming high systemic alignment to global tech spending cycles. Similarly, SBIN and ICICIBANK exhibit a strong **0.5098** correlation.
2. **Inter-Sector Diversification Potential:** IT equities exhibit low correlation against Banking equities ($\rho \approx 0.18 - 0.23$). Constructing a cross-sector portfolio combining Banking with IT provided significant variance dampening.
3. **Benchmark Sensitivity:** Reliance (0.6868), ICICI Bank (0.6625), and SBI (0.6482) exhibit the highest correlation to the NIFTY 50 index, underscoring their dominant market capitalization weights.

---

## 9. Web Dashboard Architecture & Client Presentation Layer

The web dashboard is delivered as a 100% static client-side web application hosted on GitHub Pages (`docs/`). It requires zero backend infrastructure, runs without external database connections, and operates without local CSV file dependencies.

### 9.1 Technical Structure
- **`docs/index.html`:** Semantic HTML5 structure structured into a 3-tab PowerBI corporate financial layout:
  - **Tab 1: Executive Overview Cockpit** (4 Paired KPI cards, Normalized Price Performance base-100 chart, Risk-Return Efficiency Map, 52-Week Range Position gauge, Executive Performance & Risk Summary table).
  - **Tab 2: Technical & Price Action** (Candlestick chart with proportionally adjusted OHLC, toggleable SMA-20, SMA-50, SMA-200, EMA-20 ribbons, Bollinger Bands, discrete Golden/Death cross markers, continuous regime badge, RSI-14 oscillator, and traded volume with 20-day SMA).
  - **Tab 3: Risk & Diversification** (Underwater drawdown profile, 30-day rolling volatility comparison, and square-aspect cross-asset correlation matrix heatmap).
- **`docs/style.css`:** PowerBI corporate financial theme (slate `#0f172a`, off-white `#f8fafc`, pure white `#ffffff`, high-contrast typography, zero layout shift, responsive multi-breakpoint grid).
- **`docs/app.js`:** Pure JavaScript presentation controller.
  - Dynamically wires instrument and date range slicers.
  - Implements **Benchmark-First Ordering**: NIFTY 50 (`^NSEI`) is permanently pinned as the first row.
  - Implements **Date Range Consistency**: Summary table headers and metric values dynamically adapt to selected presets (**5Y, 3Y, 1Y, YTD**) using precomputed values from `docs/dashboard_data.js`.
  - Preserves **Fixed Anchors**: `5-Yr CAGR (%)`, `Last Close`, and rolling `52W Range` remain constant across date presets.
  - Interactive table sorting sorts equities while preserving the benchmark at Row 1.
- **`docs/dashboard_data.js`:** Self-contained JSON-in-JS data bundle loaded via `<script>` tag, ensuring complete offline availability and zero CORS/XHR local file fetch restrictions.

---

## 10. Quality Assurance, Automated Testing & Verification Suite

The repository incorporates an enterprise-grade testing strategy divided into distinct test categories:

### 10.1 Automated Pytest Regression Suite
The automated test suite in `tests/` covers:
- `test_cleaner.py`: Deduplication, rejection of non-positive close records, proportional OHLC adjustment, fallback factor verification.
- `test_feature_engineering.py`: Exact CAGR mathematical formulas, Bessel-corrected volatility ($\text{ddof}=1$), $(1 + 0.065)^{1/252} - 1$ risk-free compounding, Sharpe ratio calculations, pairwise Beta, Wilder RSI-14 edge case safety, and rolling 52W high/low warm-up ($251\text{ NaNs}$).
- `test_dashboard_exporter.py`: Schema validation, multi-period export verification (5Y, 3Y, 1Y, YTD), single source of truth conformity.
- `test_data_loader.py`: Raw snapshot archival, MultiIndex flattening, trading calendar preservation.
- `test_pipeline_orchestrator.py`: Stage sequence gating, non-zero failure exit code enforcement, and centralized logging to `logs/pipeline.log`.
- `test_live_yfinance.py`: Isolated live network integration test (skipped by default in offline environments).

**Test Execution Outcome:**
```
======================= 47 passed, 1 skipped in 16.51s =======================
```

### 10.2 Chrome DevTools Protocol (CDP) Browser Automation Suite
A dedicated headless Chrome test suite verifies DOM layout, slicer interactions, and rendering integrity across all tabs and viewports:
- 38 automated browser assertions executed with **38/38 passing (0 failures)**.
- 0px horizontal scroll overflow verified across all viewports.
- Reset button cleanly restores 5Y baseline, resets dynamic headers, and clears sort indicators.

---

## 11. Assumptions, Proxy Limitations & Educational Disclaimer

### 11.1 Methodological Assumptions
1. **Constant Risk-Free Rate:** The 6.50% p.a. yield on the 10-Year Indian Government Security (G-Sec) is treated as a static proxy throughout the 5-year horizon. In reality, sovereign yields fluctuated between 6.0% and 7.5% over the 2021–2026 monetary tightening and easing cycles.
2. **Transaction Costs & Slippage:** Return calculations do not incorporate brokerage fees, Securities Transaction Tax (STT), exchange turnover charges, or liquidity slippage.
3. **Reinvestment of Dividends:** Analysis utilizes Adjusted Close prices provided by Yahoo Finance, which adjust for cash dividends, stock splits, and rights issues under standard accounting conventions.

### 11.2 Statutory Educational Disclaimer
> **IMPORTANT NOTICE:**  
> This project, technical report, and associated web dashboard were engineered strictly for academic, educational, and quantitative research purposes as part of the Diploma in Financial Engineering curriculum. The metrics, analysis, and visual representations contained herein do NOT constitute financial, investment, tax, or legal advice. Historical performance is no guarantee of future returns.

---

**Report Certification:**  
*Prepared and certified for academic portfolio review, GitHub showcase deployment, and institutional quantitative evaluation.*
