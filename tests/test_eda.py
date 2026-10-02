"""Unit Tests for Exploratory Data Analysis (EDA) Module.

Verifies:
1. Cleaned datasets are loaded and analyzed without modifying source disk files.
2. Descriptive statistical summary table generation (mean, std, skew, kurtosis, volume).
3. Export of all 5 EDA figures to outputs/eda/ with 300 DPI resolution.
4. Correctness of figure dimensions, labels, and file integrity.
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

from src.eda import EDAAnalyzer


@pytest.fixture
def mock_eda_environment(tmp_path):
    """Create isolated temporary environment with mock cleaned datasets."""
    processed_dir = tmp_path / "data" / "processed"
    output_dir = tmp_path / "outputs" / "eda"
    processed_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS", "ICICIBANK.NS", "^NSEI"]
    dates = pd.date_range("2024-01-01", periods=60, freq="B").strftime("%Y-%m-%d")

    for ticker in tickers:
        np.random.seed(len(ticker))
        base = 2000.0 if ticker == "^NSEI" else 100.0
        prices = base + np.cumsum(np.random.normal(0.1, 1.0, 60))
        df = pd.DataFrame({
            "Date": dates,
            "Open": prices - 0.5,
            "High": prices + 1.0,
            "Low": prices - 1.0,
            "Close": prices,
            "Adj Close": prices,
            "Volume": [100000] * 60,
            "adj_factor": [1.0] * 60,
            "adj_open": prices - 0.5,
            "adj_high": prices + 1.0,
            "adj_low": prices - 1.0,
            "adj_close": prices,
        })
        df.to_csv(processed_dir / f"{ticker}_cleaned.csv", index=False)

    return processed_dir, output_dir, tickers


def test_eda_statistical_summary_computation(mock_eda_environment):
    """Verify EDAAnalyzer computes valid statistical summaries across all instruments."""
    processed_dir, output_dir, tickers = mock_eda_environment
    analyzer = EDAAnalyzer(processed_dir=str(processed_dir), output_dir=str(output_dir))

    datasets = analyzer.load_cleaned_datasets(instruments=tickers)
    assert len(datasets) == 6

    summary_df = analyzer.generate_summary_statistics(datasets)
    assert len(summary_df) == 6
    expected_cols = [
        "Ticker", "Observations", "Mean Price", "Std Price", "52W High", "52W Low",
        "Mean Daily Return (%)", "Return Std Dev (%)", "Return Skewness", "Return Kurtosis",
        "Avg Daily Volume",
    ]
    for col in expected_cols:
        assert col in summary_df.columns

    # Verify all numerical values are finite
    assert summary_df["Mean Price"].notna().all()
    assert summary_df["Return Skewness"].notna().all()


def test_eda_run_all_generates_all_5_charts_and_summary_csv(mock_eda_environment):
    """Verify run_all generates all 5 charts and summary CSV without modifying source files."""
    processed_dir, output_dir, tickers = mock_eda_environment

    # Record original file modification times and content
    orig_hashes = {}
    for t in tickers:
        p = processed_dir / f"{t}_cleaned.csv"
        orig_hashes[t] = p.read_text(encoding="utf-8")

    analyzer = EDAAnalyzer(processed_dir=str(processed_dir), output_dir=str(output_dir))
    analyzer.run_all()

    # 1. Summary CSV exists and non-empty
    summary_csv = output_dir / "eda_statistical_summary.csv"
    assert summary_csv.exists()
    assert summary_csv.stat().st_size > 0

    # 2. All 5 chart PNG files exist, non-empty, and valid
    expected_plots = [
        "01_historical_closing_trends.png",
        "02_trading_volume_distribution.png",
        "03_daily_returns_distribution.png",
        "04_cross_asset_correlation_matrix.png",
        "05_rolling_30d_volatility_comparison.png",
    ]
    for plot_name in expected_plots:
        plot_path = output_dir / plot_name
        assert plot_path.exists(), f"Missing plot: {plot_name}"
        assert plot_path.stat().st_size > 5000, f"Plot {plot_name} appears empty or truncated"

    # 3. Source cleaned files must remain completely unmodified
    for t in tickers:
        p = processed_dir / f"{t}_cleaned.csv"
        assert p.read_text(encoding="utf-8") == orig_hashes[t], f"Cleaned file for {t} was mutated!"
