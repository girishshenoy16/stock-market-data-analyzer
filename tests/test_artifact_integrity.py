"""Artifact Integrity and Repository Audit Tests.

Audits the actual generated outputs in the repository through Task 8.1:
1. Raw snapshots in data/raw/ and timestamped copies in data/raw/archive/.
2. Cleaned datasets in data/processed/ and cleaning audit JSON in outputs/reports/.
3. 5 Exploratory Data Analysis figures and summary table in outputs/eda/.
4. 6 Engineered single-source-of-truth datasets and market_summary_metrics.csv in data/processed/.
5. 18 Publication-quality analytical charts in outputs/charts/.
6. Web dashboard bundle in docs/dashboard_data.js with exact data lineage consistency.
"""

import json
from pathlib import Path
import re
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_TICKERS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS", "ICICIBANK.NS", "^NSEI"]


def test_raw_snapshots_and_archives_exist():
    """Verify active raw CSV files and immutable timestamped archives exist and are non-empty."""
    raw_dir = PROJECT_ROOT / "data" / "raw"
    archive_dir = raw_dir / "archive"

    assert raw_dir.exists(), "data/raw directory must exist."
    assert archive_dir.exists(), "data/raw/archive directory must exist."

    for ticker in DEFAULT_TICKERS:
        raw_file = raw_dir / f"{ticker}_raw.csv"
        assert raw_file.exists(), f"Active raw file missing for {ticker}: {raw_file}"
        assert raw_file.stat().st_size > 1000, f"Raw file {raw_file} appears truncated"

        archives = list(archive_dir.glob(f"{ticker}_raw_*.csv"))
        assert len(archives) >= 1, f"Missing timestamped archive for {ticker} in {archive_dir}"


def test_cleaned_datasets_and_audit_report_exist():
    """Verify cleaned CSV files and cleaning audit report exist and match record counts."""
    processed_dir = PROJECT_ROOT / "data" / "processed"
    audit_file = PROJECT_ROOT / "outputs" / "reports" / "data_cleaning_audit.json"

    assert processed_dir.exists()
    assert audit_file.exists(), f"Audit file missing: {audit_file}"

    audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
    audit_records = audit_data["audit_records"]

    for ticker in DEFAULT_TICKERS:
        cleaned_file = processed_dir / f"{ticker}_cleaned.csv"
        assert cleaned_file.exists(), f"Cleaned file missing: {cleaned_file}"
        df = pd.read_csv(cleaned_file)
        assert len(df) > 1000, f"Cleaned file {cleaned_file} has insufficient rows"
        assert ticker in audit_records
        assert audit_records[ticker]["cleaned_rows"] == len(df)


def test_eda_artifacts_exist_and_valid():
    """Verify all 5 EDA figures and eda_statistical_summary.csv exist in outputs/eda/."""
    eda_dir = PROJECT_ROOT / "outputs" / "eda"
    assert eda_dir.exists()

    summary_csv = eda_dir / "eda_statistical_summary.csv"
    assert summary_csv.exists()
    df_summary = pd.read_csv(summary_csv)
    assert len(df_summary) == 6

    expected_charts = [
        "01_historical_closing_trends.png",
        "02_trading_volume_distribution.png",
        "03_daily_returns_distribution.png",
        "04_cross_asset_correlation_matrix.png",
        "05_rolling_30d_volatility_comparison.png",
    ]
    for chart_name in expected_charts:
        chart_file = eda_dir / chart_name
        assert chart_file.exists(), f"Missing EDA chart: {chart_file}"
        assert chart_file.stat().st_size > 50000, f"EDA chart {chart_file} appears too small (<50KB)"


def test_feature_engineered_datasets_and_summary_metrics_exist():
    """Verify 6 engineered CSVs and market_summary_metrics.csv exist and are valid."""
    processed_dir = PROJECT_ROOT / "data" / "processed"
    summary_file = processed_dir / "market_summary_metrics.csv"
    assert summary_file.exists()

    summary_df = pd.read_csv(summary_file)
    assert len(summary_df) == 6
    assert list(summary_df["ticker"]) == DEFAULT_TICKERS

    for ticker in DEFAULT_TICKERS:
        eng_file = processed_dir / f"{ticker}_engineered.csv"
        assert eng_file.exists(), f"Engineered dataset missing: {eng_file}"
        df = pd.read_csv(eng_file)
        assert len(df) > 1000

        # Check required columns
        expected_cols = [
            "Date", "Open", "High", "Low", "Close", "Adj Close", "Volume",
            "adj_factor", "adj_open", "adj_high", "adj_low", "adj_close",
            "daily_return", "log_return", "cumulative_return", "normalized_price",
            "sma_20", "sma_50", "sma_200", "ema_20",
            "golden_cross_event", "death_cross_event", "bullish_regime",
            "bb_middle", "bb_upper", "bb_lower",
            "rsi_14", "rolling_vol_30d", "drawdown",
            "volume_sma_20", "volume_spike_ratio",
            "rolling_52w_high", "rolling_52w_low",
        ]
        for col in expected_cols:
            assert col in df.columns, f"Column {col} missing in {eng_file}"


def test_static_visualizer_18_charts_exist():
    """Verify exactly 18 publication-quality charts exist in outputs/charts/."""
    charts_dir = PROJECT_ROOT / "outputs" / "charts"
    assert charts_dir.exists()

    expected_suffixes = [
        "_trend_indicators.png",
        "_bollinger_rsi.png",
        "_drawdown_underwater.png",
    ]

    total_found = 0
    for ticker in DEFAULT_TICKERS:
        for suffix in expected_suffixes:
            chart_file = charts_dir / f"{ticker}{suffix}"
            assert chart_file.exists(), f"Missing static chart: {chart_file}"
            assert chart_file.stat().st_size > 50000, f"Chart {chart_file} appears too small (<50KB)"
            total_found += 1

    assert total_found == 18, f"Expected 18 charts, found {total_found}"


def test_dashboard_data_js_bundle_integrity_and_data_lineage():
    """Verify docs/dashboard_data.js strictly matches engineered CSVs and summary metrics."""
    js_file = PROJECT_ROOT / "docs" / "dashboard_data.js"
    assert js_file.exists(), "docs/dashboard_data.js must exist."

    content = js_file.read_text(encoding="utf-8")
    assert content.startswith("// Stock Market Data Analyzer")
    assert "window.STOCK_DASHBOARD_DATA =" in content

    match = re.search(r"window\.STOCK_DASHBOARD_DATA\s*=\s*(\{.*\});", content, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1))

    # Schema checks
    assert data["metadata"]["schema_version"] == "1.0.0"
    assert data["metadata"]["methodology_version"] == "2026.1"
    assert data["metadata"]["instruments"] == DEFAULT_TICKERS
    assert data["metadata"]["provenance_reference"] == "data/processed/{TICKER}_engineered.csv (Local provenance only)"

    # Verify summary metrics match market_summary_metrics.csv
    summary_csv = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "market_summary_metrics.csv")
    for csv_row, js_row in zip(summary_csv.to_dict(orient="records"), data["summary_metrics"]):
        assert csv_row["ticker"] == js_row["ticker"]
        assert pytest.approx(csv_row["cagr_pct"], rel=1e-4) == js_row["cagr_pct"]
        assert pytest.approx(csv_row["annualized_volatility_pct"], rel=1e-4) == js_row["annualized_volatility_pct"]
        assert pytest.approx(csv_row["last_close"], rel=1e-4) == js_row["last_close"]

    # Verify instrument data aligns with engineered CSVs
    for ticker in DEFAULT_TICKERS:
        csv_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / f"{ticker}_engineered.csv")
        js_inst = data["instruments_data"][ticker]

        assert len(csv_df) == len(js_inst["dates"])
        # Check last close
        assert round(float(csv_df["adj_close"].iloc[-1]), 4) == round(float(js_inst["adj_close"][-1]), 4)
        # Check first close
        assert round(float(csv_df["adj_close"].iloc[0]), 4) == round(float(js_inst["adj_close"][0]), 4)
        # Check normalized price at start is 100.0
        assert js_inst["normalized_price"][0] == 100.0
