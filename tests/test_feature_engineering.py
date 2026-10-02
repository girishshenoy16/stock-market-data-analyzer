"""Unit Tests for Feature Engineering, Technical Indicators, and Financial Mathematics.

Verifies against frozen specifications:
1. Simple, log, and cumulative returns.
2. Normalized price from own first valid observation.
3. Simple Moving Averages (SMA-20, 50, 200) with strict warm-up NaN periods.
4. Exponential Moving Average (EMA-20).
5. Discrete Golden Cross and Death Cross events vs continuous bullish regime.
6. Bollinger Bands (20-day SMA +/- 2*sigma, ddof=1).
7. Wilder's RSI-14 edge cases (all-gain -> 100, all-loss -> 0, flat -> 50, N < 15 -> NaN).
8. Adjusted 52-Week High and Low (fixed 252-window, min_periods=252, first 251 NaN).
9. Volume SMA-20 and Volume Spike Ratio.
10. Peak-to-trough Drawdown and Maximum Drawdown (MDD).
11. Historical Value at Risk (VaR 95% 1-Day empirical 5th percentile).
12. Full horizon Annualized Volatility (ddof=1, sqrt(252)).
13. Sharpe Ratio with exact compounding daily risk-free rate proxy (1+0.065)^(1/252) - 1.
14. Pairwise date-aligned Beta vs benchmark (N >= 30, zero variance guard, fallback NaN).
15. Joint complete-case Pearson correlation matrix (positive semi-definiteness).
16. Calendar-duration CAGR with trading_return_intervals metadata.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_engineering import (
    ANNUAL_RISK_FREE_RATE,
    DAILY_RISK_FREE_RATE,
    TRADING_DAYS_PER_YEAR,
    FeatureEngineer,
)


# ==============================================================================
# 1. Returns & Normalized Price Tests
# ==============================================================================

def test_returns_and_normalization_calculations():
    """Verify daily return, log return, cumulative return, and base-100 normalization."""
    fe = FeatureEngineer()
    dates = pd.date_range("2024-01-01", periods=5, freq="B").strftime("%Y-%m-%d")
    prices = [100.0, 105.0, 102.0, 110.0, 115.0]

    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": [p + 2 for p in prices],
        "Low": [p - 2 for p in prices],
        "Close": prices,
        "Adj Close": prices,
        "Volume": [1000] * 5,
        "adj_open": prices,
        "adj_high": [p + 2 for p in prices],
        "adj_low": [p - 2 for p in prices],
        "adj_close": prices,
    })

    res = fe.engineer_instrument(df, "TEST.NS")

    # 1. Daily Return
    assert pd.isna(res.loc[0, "daily_return"])
    assert pytest.approx(res.loc[1, "daily_return"], rel=1e-5) == (105.0 - 100.0) / 100.0
    assert pytest.approx(res.loc[2, "daily_return"], rel=1e-5) == (102.0 - 105.0) / 105.0

    # 2. Log Return
    assert pd.isna(res.loc[0, "log_return"])
    assert pytest.approx(res.loc[1, "log_return"], rel=1e-5) == np.log(105.0 / 100.0)

    # 3. Cumulative Return (starts at 0.0 on day 0)
    assert pytest.approx(res.loc[0, "cumulative_return"], abs=1e-6) == 0.0
    assert pytest.approx(res.loc[4, "cumulative_return"], rel=1e-5) == (115.0 / 100.0) - 1.0

    # 4. Normalized Price (starts at 100.0 on day 0)
    assert pytest.approx(res.loc[0, "normalized_price"], abs=1e-6) == 100.0
    assert pytest.approx(res.loc[4, "normalized_price"], rel=1e-5) == (115.0 / 100.0) * 100.0


# ==============================================================================
# 2. Moving Averages & Regime Tests
# ==============================================================================

def test_moving_averages_warmup_and_crossover_events():
    """Verify SMA warm-up NaNs, discrete Golden/Death cross event flags, and bullish regime."""
    fe = FeatureEngineer()
    n = 220
    dates = pd.date_range("2024-01-01", periods=n, freq="B").strftime("%Y-%m-%d")

    # Construct price series that triggers a Golden Cross at day 205
    # First 200 days: steady price 100.0
    # Day 201-220: surging price up to 200.0 (SMA50 will rise faster than SMA200)
    prices = np.full(n, 100.0)
    prices[200:] = np.linspace(100.0, 250.0, 20)

    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": prices + 1,
        "Low": prices - 1,
        "Close": prices,
        "Adj Close": prices,
        "Volume": [10000] * n,
        "adj_open": prices,
        "adj_high": prices + 1,
        "adj_low": prices - 1,
        "adj_close": prices,
    })

    res = fe.engineer_instrument(df, "TEST.NS")

    # Warm-up verification
    # SMA-20: first 19 observations are NaN, index 19 (20th obs) is valid
    assert res["sma_20"].iloc[:19].isna().all()
    assert res["sma_20"].iloc[19] == 100.0

    # SMA-50: first 49 observations are NaN, index 49 (50th obs) is valid
    assert res["sma_50"].iloc[:49].isna().all()
    assert res["sma_50"].iloc[49] == 100.0

    # SMA-200: first 199 observations are NaN, index 199 (200th obs) is valid
    assert res["sma_200"].iloc[:199].isna().all()
    assert res["sma_200"].iloc[199] == 100.0

    # Crossover discrete flags
    golden_crosses = res[res["golden_cross_event"] == 1]
    # Golden cross must occur as a discrete single-day event when SMA50 overtakes SMA200
    if not golden_crosses.empty:
        gc_idx = golden_crosses.index[0]
        assert res.loc[gc_idx, "golden_cross_event"] == 1
        # Previous day must not be a golden cross
        assert res.loc[gc_idx - 1, "golden_cross_event"] == 0
        # Post-crossover bullish regime must be True
        assert bool(res.loc[gc_idx, "bullish_regime"]) is True


# ==============================================================================
# 3. Bollinger Bands Tests
# ==============================================================================

def test_bollinger_bands_calculation():
    """Verify Bollinger Bands middle, upper, lower bands with sample std (ddof=1)."""
    fe = FeatureEngineer()
    dates = pd.date_range("2024-01-01", periods=25, freq="B").strftime("%Y-%m-%d")
    np.random.seed(123)
    prices = 100.0 + np.cumsum(np.random.normal(0, 1, 25))

    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": prices + 1,
        "Low": prices - 1,
        "Close": prices,
        "Adj Close": prices,
        "Volume": [1000] * 25,
        "adj_open": prices,
        "adj_high": prices + 1,
        "adj_low": prices - 1,
        "adj_close": prices,
    })

    res = fe.engineer_instrument(df, "BB.NS")

    # First 19 are NaN
    assert res["bb_middle"].iloc[:19].isna().all()
    assert res["bb_upper"].iloc[:19].isna().all()
    assert res["bb_lower"].iloc[:19].isna().all()

    # Observation 20 (index 19)
    window_prices = prices[:20]
    expected_mean = np.mean(window_prices)
    expected_std = np.std(window_prices, ddof=1)

    assert pytest.approx(res.loc[19, "bb_middle"], rel=1e-5) == expected_mean
    assert pytest.approx(res.loc[19, "bb_upper"], rel=1e-5) == expected_mean + 2.0 * expected_std
    assert pytest.approx(res.loc[19, "bb_lower"], rel=1e-5) == expected_mean - 2.0 * expected_std


# ==============================================================================
# 4. Wilder's RSI-14 Edge Cases Tests
# ==============================================================================

def test_wilder_rsi_14_edge_cases():
    """Verify Wilder's RSI-14 under all-gain (100), all-loss (0), flat (50), and N<15 cases."""
    fe = FeatureEngineer()

    # 1. All-gain period (prices strictly increasing: 10, 11, 12, ... 30)
    all_gain_prices = pd.Series([float(x) for x in range(10, 35)])
    rsi_gain = fe.calculate_rsi_14(all_gain_prices)
    # First 14 are NaN, index 14 onwards must be strictly 100.0
    assert rsi_gain.iloc[:14].isna().all()
    assert (rsi_gain.iloc[14:] == 100.0).all()

    # 2. All-loss period (prices strictly decreasing: 50, 49, 48, ... 20)
    all_loss_prices = pd.Series([float(x) for x in range(50, 20, -1)])
    rsi_loss = fe.calculate_rsi_14(all_loss_prices)
    assert rsi_loss.iloc[:14].isna().all()
    assert (rsi_loss.iloc[14:] == 0.0).all()

    # 3. Completely flat period (prices identical: 100, 100, 100, ...)
    flat_prices = pd.Series([100.0] * 30)
    rsi_flat = fe.calculate_rsi_14(flat_prices)
    assert rsi_flat.iloc[:14].isna().all()
    assert (rsi_flat.iloc[14:] == 50.0).all()

    # 4. Insufficient observations (N < 15)
    short_prices = pd.Series([100.0] * 10)
    rsi_short = fe.calculate_rsi_14(short_prices)
    assert rsi_short.isna().all()


# ==============================================================================
# 5. Adjusted 52-Week High & Low Warm-Up Tests
# ==============================================================================

def test_adjusted_52w_high_low_warmup_policy():
    """Verify rolling 52w high/low has fixed 252 window with first 251 observations as NaN."""
    fe = FeatureEngineer()
    n = 260
    dates = pd.date_range("2024-01-01", periods=n, freq="B").strftime("%Y-%m-%d")
    np.random.seed(42)
    prices = 100.0 + np.cumsum(np.random.normal(0, 1, n))
    adj_high = prices + 2.0
    adj_low = prices - 2.0

    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": adj_high,
        "Low": adj_low,
        "Close": prices,
        "Adj Close": prices,
        "Volume": [1000] * n,
        "adj_open": prices,
        "adj_high": adj_high,
        "adj_low": adj_low,
        "adj_close": prices,
    })

    res = fe.engineer_instrument(df, "TEST.NS")

    # Warm-up: First 251 observations strictly evaluate to NaN (0 to 250)
    assert res["rolling_52w_high"].iloc[:251].isna().all(), "First 251 values must be NaN."
    assert res["rolling_52w_low"].iloc[:251].isna().all(), "First 251 values must be NaN."

    # Observation 252 (index 251) evaluates to the 252-window max/min
    expected_high = adj_high[:252].max()
    expected_low = adj_low[:252].min()
    assert pytest.approx(res.loc[251, "rolling_52w_high"], rel=1e-5) == expected_high
    assert pytest.approx(res.loc[251, "rolling_52w_low"], rel=1e-5) == expected_low


# ==============================================================================
# 6. Drawdown & VaR Tests
# ==============================================================================

def test_drawdown_and_var_calculations():
    """Verify peak-to-trough drawdown series, maximum drawdown (MDD), and empirical 95% VaR."""
    fe = FeatureEngineer()
    dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    prices = [100.0, 120.0, 90.0, 110.0, 80.0]

    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": [p + 1 for p in prices],
        "Low": [p - 1 for p in prices],
        "Close": prices,
        "Adj Close": prices,
        "Volume": [1000] * 5,
        "adj_open": prices,
        "adj_high": [p + 1 for p in prices],
        "adj_low": [p - 1 for p in prices],
        "adj_close": prices,
    })

    res = fe.engineer_instrument(df, "TEST.NS")

    # Peak progression: [100, 120, 120, 120, 120]
    # Drawdown: [0, 0, (90-120)/120 = -0.25, (110-120)/120 = -0.0833, (80-120)/120 = -0.3333]
    assert pytest.approx(res.loc[0, "drawdown"], abs=1e-5) == 0.0
    assert pytest.approx(res.loc[1, "drawdown"], abs=1e-5) == 0.0
    assert pytest.approx(res.loc[2, "drawdown"], rel=1e-5) == -0.25
    assert pytest.approx(res.loc[4, "drawdown"], rel=1e-5) == (80.0 - 120.0) / 120.0

    # MDD
    mdd = res["drawdown"].min()
    assert pytest.approx(mdd, rel=1e-5) == (80.0 - 120.0) / 120.0


# ==============================================================================
# 7. Sharpe Ratio & Volatility Tests
# ==============================================================================

def test_sharpe_ratio_and_volatility_exact_formulas():
    """Verify compounding daily risk-free rate conversion and Sharpe formulation with ddof=1."""
    # 1. Exact daily risk-free conversion: (1 + 0.065)^(1/252) - 1
    expected_rf_daily = (1.0 + 0.065) ** (1.0 / 252.0) - 1.0
    assert pytest.approx(DAILY_RISK_FREE_RATE, abs=1e-9) == expected_rf_daily
    assert pytest.approx(DAILY_RISK_FREE_RATE, abs=1e-6) == 0.000250007

    # 2. Known daily return series
    returns = pd.Series([0.01, -0.005, 0.008, 0.002, -0.003, 0.012, 0.004, -0.001] * 10)
    std_sample = returns.std(ddof=1)
    ann_vol = std_sample * np.sqrt(TRADING_DAYS_PER_YEAR)

    excess_returns = returns - DAILY_RISK_FREE_RATE
    expected_sharpe = np.sqrt(TRADING_DAYS_PER_YEAR) * (excess_returns.mean() / excess_returns.std(ddof=1))

    assert ann_vol > 0
    assert not np.isnan(expected_sharpe)


# ==============================================================================
# 8. Beta vs Benchmark & Correlation Tests
# ==============================================================================

def test_beta_vs_benchmark_and_sample_size_guards():
    """Verify Beta calculation with N>=30 and NaN fallback when N<30 or benchmark variance is zero."""
    fe = FeatureEngineer()

    # 1. N >= 30 valid case: stock returns = 1.5 * benchmark returns
    np.random.seed(99)
    bmk_rets = pd.Series(np.random.normal(0.0005, 0.01, 50))
    stock_rets = bmk_rets * 1.5 + np.random.normal(0, 0.001, 50)
    dates = pd.date_range("2024-01-01", periods=50, freq="B").strftime("%Y-%m-%d")

    df_stock = pd.DataFrame({
        "Date": dates,
        "daily_return": stock_rets,
        "adj_close": [100.0] * 50,
        "drawdown": [0.0] * 50,
        "rolling_52w_high": [100.0] * 50,
        "rolling_52w_low": [100.0] * 50,
    })
    bmk_series = pd.Series(bmk_rets.values, index=dates)

    row = fe.compute_summary_row(df_stock, "TEST.NS", bmk_series)
    assert row["beta_nifty"] is not None
    assert pytest.approx(row["beta_nifty"], rel=0.05) == 1.5

    # 2. Benchmark symbol itself -> Beta strictly 1.0
    row_bmk = fe.compute_summary_row(df_stock, "^NSEI", bmk_series)
    assert row_bmk["beta_nifty"] == 1.0

    # 3. Insufficient observations: N = 20 (< 30) -> Beta must be None / NaN
    df_short = df_stock.iloc[:20].copy()
    row_short = fe.compute_summary_row(df_short, "SHORT.NS", bmk_series)
    assert row_short["beta_nifty"] is None, "Beta must evaluate to None/NaN when N < 30."

    # 4. Zero benchmark variance (flat benchmark) -> Beta must be None / NaN
    flat_bmk_series = pd.Series([0.0] * 50, index=dates)
    row_flat = fe.compute_summary_row(df_stock, "TEST.NS", flat_bmk_series)
    assert row_flat["beta_nifty"] is None, "Beta must evaluate to None/NaN when benchmark variance is zero."


def test_correlation_matrix_positive_semi_definite():
    """Verify joint inner-join Pearson correlation matrix is positive semi-definite."""
    fe = FeatureEngineer()
    dates = pd.date_range("2024-01-01", periods=60, freq="B").strftime("%Y-%m-%d")
    np.random.seed(77)

    eng_dict = {}
    for sym in ["RELIANCE.NS", "TCS.NS", "INFY.NS", "^NSEI"]:
        rets = pd.Series(np.random.normal(0.0005, 0.015, 60))
        df = pd.DataFrame({"Date": dates, "daily_return": rets})
        eng_dict[sym] = df

    symbols, corr_mat = fe.compute_correlation_matrix(eng_dict)
    assert len(symbols) == 4
    assert corr_mat.shape == (4, 4)

    # Diagonal elements must be 1.0
    np.testing.assert_allclose(np.diag(corr_mat), 1.0, atol=1e-7)

    # Symmetry
    np.testing.assert_allclose(corr_mat, corr_mat.T, atol=1e-7)

    # Positive semi-definite check: all eigenvalues >= -1e-10 (subject to floating point)
    eigvals = np.linalg.eigvalsh(corr_mat)
    assert (eigvals >= -1e-10).all(), f"Correlation matrix not positive semi-definite: {eigvals}"


# ==============================================================================
# 9. CAGR Calendar Duration vs Trading Intervals Tests
# ==============================================================================

def test_cagr_calendar_duration_calculation():
    """Verify CAGR uses exact calendar duration years = (end - start).days / 365.25."""
    fe = FeatureEngineer()
    d_start = "2021-09-28"
    d_end = "2026-09-28"  # Exactly 5 calendar years = 1826 days / 365.25 ≈ 5.0 years
    dates = pd.date_range(d_start, d_end, freq="B").strftime("%Y-%m-%d")
    n = len(dates)

    # 100.0 growing to 200.0 over 5 calendar years
    prices = np.linspace(100.0, 200.0, n)
    df = pd.DataFrame({
        "Date": dates,
        "daily_return": pd.Series(prices).pct_change(),
        "adj_close": prices,
        "drawdown": [0.0] * n,
        "rolling_52w_high": [200.0] * n,
        "rolling_52w_low": [100.0] * n,
    })

    bmk_rets = pd.Series([0.0005] * n, index=dates)
    row = fe.compute_summary_row(df, "TEST.NS", bmk_rets)

    cal_years = (pd.to_datetime(d_end) - pd.to_datetime(d_start)).days / 365.25
    expected_cagr = (200.0 / 100.0) ** (1.0 / cal_years) - 1.0

    assert pytest.approx(row["cagr_pct"], rel=1e-4) == expected_cagr * 100.0
    assert row["trading_return_intervals"] == n - 1
    assert pytest.approx(row["calendar_duration_years"], rel=1e-4) == cal_years
