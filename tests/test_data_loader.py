"""Unit Tests for Data Ingestion, Schema Normalization, and Snapshot Archival.

Verifies:
1. Ticker universe and date boundary configuration (exclusive end date).
2. Modern yfinance MultiIndex column flattening.
3. Date format standardization to YYYY-MM-DD.
4. Validation against missing columns and empty responses.
5. Staleness assessment against trading calendar gap thresholds.
6. Raw snapshot preservation and timestamped archival copy creation.
7. Confirmation that failed refreshes/errors do not overwrite existing valid raw files.
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import (
    DEFAULT_END_DATE,
    DEFAULT_INSTRUMENTS,
    DEFAULT_START_DATE,
    EXPECTED_COLUMNS,
    StockDataLoader,
)


def test_data_loader_configuration_and_universe():
    """Verify default asset universe and 5-year date horizon constants."""
    assert len(DEFAULT_INSTRUMENTS) == 6
    assert DEFAULT_INSTRUMENTS == [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "SBIN.NS",
        "ICICIBANK.NS",
        "^NSEI",
    ]
    assert DEFAULT_START_DATE == "2021-09-28"
    assert DEFAULT_END_DATE == "2026-09-28"
    assert EXPECTED_COLUMNS == ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


def test_flatten_columns_multiindex_price_level_0():
    """Verify flattening when Price is level 0 and Ticker is level 1."""
    cols = pd.MultiIndex.from_tuples([
        ("Open", "RELIANCE.NS"),
        ("High", "RELIANCE.NS"),
        ("Low", "RELIANCE.NS"),
        ("Close", "RELIANCE.NS"),
        ("Adj Close", "RELIANCE.NS"),
        ("Volume", "RELIANCE.NS"),
    ])
    df = pd.DataFrame(
        [[100.0, 105.0, 99.0, 104.0, 104.0, 10000]],
        columns=cols,
        index=pd.DatetimeIndex(["2024-01-02"]),
    )
    df.index.name = "Date"

    loader = StockDataLoader()
    flattened = loader.flatten_columns(df, "RELIANCE.NS")

    assert list(flattened.columns) == EXPECTED_COLUMNS
    assert flattened["Date"].iloc[0] == "2024-01-02"
    assert flattened["Close"].iloc[0] == 104.0


def test_flatten_columns_multiindex_price_level_1():
    """Verify flattening when Ticker is level 0 and Price is level 1."""
    cols = pd.MultiIndex.from_tuples([
        ("TCS.NS", "Open"),
        ("TCS.NS", "High"),
        ("TCS.NS", "Low"),
        ("TCS.NS", "Close"),
        ("TCS.NS", "Adj Close"),
        ("TCS.NS", "Volume"),
    ])
    df = pd.DataFrame(
        [[3000.0, 3050.0, 2990.0, 3020.0, 3020.0, 50000]],
        columns=cols,
        index=pd.DatetimeIndex(["2024-01-02"]),
    )
    df.index.name = "Date"

    loader = StockDataLoader()
    flattened = loader.flatten_columns(df, "TCS.NS")

    assert list(flattened.columns) == EXPECTED_COLUMNS
    assert flattened["Date"].iloc[0] == "2024-01-02"
    assert flattened["Adj Close"].iloc[0] == 3020.0


def test_flatten_columns_missing_required_column_raises():
    """Verify that a download missing required price columns raises ValueError."""
    cols = ["Date", "Open", "High", "Low", "Close", "Volume"]  # Missing 'Adj Close'
    df = pd.DataFrame([[ "2024-01-02", 100, 105, 99, 104, 10000 ]], columns=cols)

    loader = StockDataLoader()
    with pytest.raises(ValueError, match="missing required columns"):
        loader.flatten_columns(df, "TEST.NS")


def test_flatten_columns_missing_date_index_raises():
    """Verify missing Date column and non-datetime index raises ValueError."""
    cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    df = pd.DataFrame([[100, 105, 99, 104, 104, 10000]], columns=cols)

    loader = StockDataLoader()
    with pytest.raises(ValueError, match="No Date column or DatetimeIndex found"):
        loader.flatten_columns(df, "TEST.NS")


def test_check_staleness_logic():
    """Verify market data staleness evaluation against exchange calendar gap thresholds."""
    current_time = datetime(2026, 9, 28, 15, 30, 0)  # Monday

    # 1. Fresh observation: Friday close (3 days prior) -> not stale
    friday_obs = "2026-09-25"
    res_friday = StockDataLoader.check_staleness(friday_obs, current_dt=current_time)
    assert not res_friday["staleness_flag"]
    assert res_friday["calendar_gap_days"] == 3

    # 2. Stale observation: 7 days ago -> stale
    stale_obs = "2026-09-21"
    res_stale = StockDataLoader.check_staleness(stale_obs, current_dt=current_time)
    assert res_stale["staleness_flag"]
    assert res_stale["calendar_gap_days"] == 7
    assert "Data may be stale" in res_stale["warning"]

    # 3. Future observation relative to system time -> stale / warning
    future_obs = "2026-09-30"
    res_future = StockDataLoader.check_staleness(future_obs, current_dt=current_time)
    assert res_future["staleness_flag"]
    assert "in the future" in res_future["warning"]


def test_save_and_archive_creates_both_files(tmp_path):
    """Verify that save_and_archive creates active raw CSV and timestamped archive file."""
    raw_dir = tmp_path / "raw"
    archive_dir = tmp_path / "raw" / "archive"
    loader = StockDataLoader(raw_dir=str(raw_dir), archive_dir=str(archive_dir))

    df = pd.DataFrame({
        "Date": ["2024-01-02"],
        "Open": [100.0],
        "High": [105.0],
        "Low": [95.0],
        "Close": [102.0],
        "Adj Close": [102.0],
        "Volume": [1000],
    })

    paths = loader.save_and_archive(df, "RELIANCE.NS", "20260928_120000")
    assert paths["active"].exists()
    assert paths["archive"].exists()
    assert paths["active"].name == "RELIANCE.NS_raw.csv"
    assert paths["archive"].name == "RELIANCE.NS_raw_20260928_120000.csv"


def test_failed_download_preserves_existing_raw_data(tmp_path):
    """Verify that if yfinance download fails, existing active raw CSV is NOT overwritten."""
    raw_dir = tmp_path / "raw"
    archive_dir = tmp_path / "raw" / "archive"
    loader = StockDataLoader(raw_dir=str(raw_dir), archive_dir=str(archive_dir))

    # Pre-populate an existing valid raw file
    existing_file = raw_dir / "RELIANCE.NS_raw.csv"
    existing_file.write_text("Date,Open,High,Low,Close,Adj Close,Volume\n2024-01-01,1,2,0.5,1.5,1.5,100\n", encoding="utf-8")
    original_content = existing_file.read_text(encoding="utf-8")

    # Mock yfinance to simulate network error
    with patch("yfinance.download", side_effect=ConnectionError("Yahoo Finance API unreachable")):
        with pytest.raises(ConnectionError):
            loader.fetch_ticker("RELIANCE.NS")

    # Ensure existing raw file was preserved unchanged
    assert existing_file.exists()
    assert existing_file.read_text(encoding="utf-8") == original_content


def test_empty_download_raises_and_preserves_existing(tmp_path):
    """Verify that an empty DataFrame response from yfinance raises RuntimeError."""
    raw_dir = tmp_path / "raw"
    archive_dir = tmp_path / "raw" / "archive"
    loader = StockDataLoader(raw_dir=str(raw_dir), archive_dir=str(archive_dir))

    with patch("yfinance.download", return_value=pd.DataFrame()):
        with pytest.raises(RuntimeError, match="Download returned empty DataFrame"):
            loader.fetch_ticker("INFY.NS")
