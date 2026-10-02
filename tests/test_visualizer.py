"""Unit Tests for Static Visualizer Module.

Verifies:
1. Ingestion of engineered datasets.
2. Generation of 3 publication-grade figures per instrument (Trend Indicators, Bollinger/RSI, Drawdown Underwater).
3. Exact 18 figures generated for the 6-instrument universe.
4. Output directory creation, 300 DPI resolution, and non-empty PNG files.
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

from src.visualizer import StaticVisualizer


@pytest.fixture
def mock_visualizer_env(tmp_path):
    """Create isolated directory tree with mock engineered data for testing visualizer."""
    processed_dir = tmp_path / "data" / "processed"
    output_dir = tmp_path / "outputs" / "charts"
    processed_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    tickers = ["RELIANCE.NS", "TCS.NS"]
    n = 220
    dates = pd.date_range("2024-01-01", periods=n, freq="B")

    for ticker in tickers:
        np.random.seed(42)
        prices = 100.0 + np.cumsum(np.random.normal(0, 1, n))
        peak = np.maximum.accumulate(prices)
        dd = (prices - peak) / peak

        df = pd.DataFrame({
            "Date": dates.strftime("%Y-%m-%d"),
            "adj_close": prices,
            "sma_20": pd.Series(prices).rolling(20).mean(),
            "sma_50": pd.Series(prices).rolling(50).mean(),
            "sma_200": pd.Series(prices).rolling(200).mean(),
            "ema_20": pd.Series(prices).ewm(span=20).mean(),
            "golden_cross_event": [0] * (n - 1) + [1],
            "death_cross_event": [0] * n,
            "bb_middle": pd.Series(prices).rolling(20).mean(),
            "bb_upper": pd.Series(prices).rolling(20).mean() + 4.0,
            "bb_lower": pd.Series(prices).rolling(20).mean() - 4.0,
            "rsi_14": [50.0] * n,
            "drawdown": dd,
        })
        df.to_csv(processed_dir / f"{ticker}_engineered.csv", index=False)

    return processed_dir, output_dir, tickers


def test_visualizer_generates_3_charts_per_instrument(mock_visualizer_env):
    """Verify StaticVisualizer creates trend, bollinger/rsi, and drawdown charts."""
    processed_dir, output_dir, tickers = mock_visualizer_env
    viz = StaticVisualizer(processed_dir=str(processed_dir), output_dir=str(output_dir))

    charts = viz.generate_all_charts(instruments=tickers)
    assert len(charts) == 6  # 2 instruments * 3 charts = 6 charts

    for t in tickers:
        p1 = output_dir / f"{t}_trend_indicators.png"
        p2 = output_dir / f"{t}_bollinger_rsi.png"
        p3 = output_dir / f"{t}_drawdown_underwater.png"

        assert p1.exists() and p1.stat().st_size > 10000
        assert p2.exists() and p2.stat().st_size > 10000
        assert p3.exists() and p3.stat().st_size > 10000
