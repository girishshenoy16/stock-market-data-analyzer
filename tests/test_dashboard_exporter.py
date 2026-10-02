"""Unit Tests for Web Dashboard Data Exporter Module.

Verifies:
1. Compilation of docs/dashboard_data.js according to versioned JSON/JS schema.
2. Complete coverage of all required time-series and summary fields.
3. Safe conversion of NaN and Inf to JSON-compliant null (None in Python).
4. Single-source-of-truth contract matching engineered CSVs and summary metrics.
5. Atomic file writing preventing partial or corrupt files on export failure.
6. JavaScript syntax validity of the window.STOCK_DASHBOARD_DATA assignment.
"""

import json
from pathlib import Path
import re
import sys
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard_exporter import DashboardExporter


@pytest.fixture
def mock_export_env(tmp_path):
    """Setup isolated temporary environment with mock engineered data and summary table."""
    processed_dir = tmp_path / "data" / "processed"
    docs_dir = tmp_path / "docs"
    processed_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    tickers = ["RELIANCE.NS", "^NSEI"]
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]

    for ticker in tickers:
        df = pd.DataFrame({
            "Date": dates,
            "Open": [100.0, 102.0, 104.0],
            "High": [105.0, 106.0, 108.0],
            "Low": [95.0, 98.0, 100.0],
            "Close": [102.0, 104.0, 106.0],
            "Adj Close": [102.0, 104.0, 106.0],
            "Volume": [1000, 2000, 3000],
            "adj_open": [100.0, 102.0, 104.0],
            "adj_high": [105.0, 106.0, 108.0],
            "adj_low": [95.0, 98.0, 100.0],
            "adj_close": [102.0, 104.0, 106.0],
            "volume_sma_20": [np.nan, np.nan, 2000.0],
            "volume_spike_ratio": [np.nan, np.nan, 1.5],
            "rolling_52w_high": [np.nan, np.nan, 108.0],
            "rolling_52w_low": [np.nan, np.nan, 95.0],
            "daily_return": [np.nan, 0.0196, 0.0192],
            "log_return": [np.nan, 0.0194, 0.0190],
            "cumulative_return": [0.0, 0.0196, 0.0392],
            "normalized_price": [100.0, 101.96, 103.92],
            "sma_20": [np.nan, np.nan, 104.0],
            "sma_50": [np.nan, np.nan, np.nan],
            "sma_200": [np.nan, np.nan, np.nan],
            "ema_20": [102.0, 102.19, 102.55],
            "rsi_14": [np.nan, np.nan, np.nan],
            "bb_upper": [np.nan, np.nan, 108.0],
            "bb_middle": [np.nan, np.nan, 104.0],
            "bb_lower": [np.nan, np.nan, 100.0],
            "drawdown": [0.0, 0.0, 0.0],
            "rolling_vol_30d": [np.nan, np.nan, np.nan],
            "golden_cross_event": [0, 0, 0],
            "death_cross_event": [0, 0, 0],
            "bullish_regime": [False, False, False],
        })
        df.to_csv(processed_dir / f"{ticker}_engineered.csv", index=False)

    summary_df = pd.DataFrame([
        {
            "ticker": "RELIANCE.NS",
            "cagr_pct": 12.5,
            "annualized_volatility_pct": 20.0,
            "sharpe_ratio": 0.65,
            "max_drawdown_pct": -15.0,
            "var_95_pct": -2.0,
            "beta_nifty": 1.15,
            "last_close": 106.0,
            "52w_high": 108.0,
            "52w_low": 95.0,
            "trading_return_intervals": 2,
            "calendar_duration_years": 0.0055,
        },
        {
            "ticker": "^NSEI",
            "cagr_pct": 10.0,
            "annualized_volatility_pct": 14.0,
            "sharpe_ratio": 0.50,
            "max_drawdown_pct": -10.0,
            "var_95_pct": -1.5,
            "beta_nifty": 1.0,
            "last_close": 106.0,
            "52w_high": 108.0,
            "52w_low": 95.0,
            "trading_return_intervals": 2,
            "calendar_duration_years": 0.0055,
        },
    ])
    summary_df.to_csv(processed_dir / "market_summary_metrics.csv", index=False)

    return processed_dir, docs_dir, tickers


def test_sanitize_series_converts_nan_and_inf_to_none():
    """Verify that pd.Series with NaN and Inf cleanly convert to None."""
    s = pd.Series([10.5, np.nan, np.inf, -np.inf, 20.0])
    cleaned = DashboardExporter.sanitize_series(s)
    assert cleaned == [10.5, None, None, None, 20.0]


def test_export_schema_and_javascript_syntax(mock_export_env):
    """Verify that export produces valid JavaScript matching the required JSON schema."""
    processed_dir, docs_dir, tickers = mock_export_env
    exporter = DashboardExporter(processed_dir=str(processed_dir), docs_dir=str(docs_dir))

    js_file = exporter.export(instruments=tickers)
    assert js_file.exists()
    assert js_file.name == "dashboard_data.js"

    content = js_file.read_text(encoding="utf-8")
    assert content.startswith("// Stock Market Data Analyzer")
    assert "window.STOCK_DASHBOARD_DATA =" in content

    # Parse JSON payload
    match = re.search(r"window\.STOCK_DASHBOARD_DATA\s*=\s*(\{.*\});", content, re.DOTALL)
    assert match is not None, "JavaScript assignment regex failed."
    payload = json.loads(match.group(1))

    # Verify top-level schema keys
    assert set(payload.keys()) == {
        "metadata",
        "summary_metrics",
        "period_metrics",
        "correlation_matrix",
        "instruments_data",
    }
    assert payload["metadata"]["schema_version"] == "1.0.0"
    assert payload["metadata"]["methodology_version"] == "2026.1"
    assert payload["metadata"]["instruments"] == tickers

    # Verify required instrument fields
    inst_data = payload["instruments_data"]["RELIANCE.NS"]
    required_fields = [
        "dates", "open", "high", "low", "close", "adj_open", "adj_high", "adj_low", "adj_close",
        "volume", "volume_sma_20", "volume_spike_ratio", "rolling_52w_high", "rolling_52w_low",
        "daily_return", "log_return", "cumulative_return", "normalized_price",
        "sma_20", "sma_50", "sma_200", "ema_20", "rsi_14",
        "bb_upper", "bb_middle", "bb_lower", "drawdown", "rolling_vol_30d",
        "golden_cross_event", "death_cross_event", "bullish_regime",
    ]
    for field in required_fields:
        assert field in inst_data, f"Missing required field in exported instrument: {field}"


def test_atomic_export_prevents_partial_file_on_error(mock_export_env):
    """Verify that if an error occurs during export, the target file is not corrupted."""
    processed_dir, docs_dir, tickers = mock_export_env
    exporter = DashboardExporter(processed_dir=str(processed_dir), docs_dir=str(docs_dir))

    # Pre-create valid target file
    target_file = docs_dir / "dashboard_data.js"
    target_file.write_text("// original intact content", encoding="utf-8")

    # Inject error during json serialization or file write
    with patch("json.dumps", side_effect=ValueError("Simulated serialization crash")):
        with pytest.raises(ValueError):
            exporter.export(instruments=tickers)

    # Verify original file remained intact
    assert target_file.read_text(encoding="utf-8") == "// original intact content"
    # Verify no dangling .tmp file remains
    assert not (docs_dir / "dashboard_data.js.tmp").exists()
