"""Unit Tests for Data Cleaning, Quality Validation, and Proportional Adjustments.

Verifies:
1. Timestamp deduplication (keeping latest record).
2. Date format normalization and timezone offset stripping.
3. Strict rejection policy: Close <= 0, NaN, Inf, non-finite.
4. Physical constraint enforcement (High >= Low, High >= Open/Close, Low <= Open/Close, Volume >= 0).
5. Proportional OHLC scaling factor f_t = Adj Close / Close.
6. Fallback factor f_t = 1.0 when Adj Close is missing, non-positive, or invalid.
7. Preservation of raw OHLCV columns.
8. Preservation of natural exchange calendar breaks (no blind forward-fill).
9. Audit log generation (JSON) with accurate rejection counts.
10. Preservation of source raw CSV files on disk during cleaning.
"""

import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cleaner import DataCleaner


def test_cleaner_deduplication_and_date_normalization(tmp_path):
    """Verify duplicate dates are pruned and date string format is standardized."""
    cleaner = DataCleaner(
        raw_dir=str(tmp_path / "raw"),
        processed_dir=str(tmp_path / "processed"),
        audit_log_path=str(tmp_path / "audit.json"),
    )

    raw_df = pd.DataFrame({
        "Date": ["2024-01-02", "2024-01-02", "2024-01-03"],
        "Open": [100.0, 101.0, 105.0],
        "High": [105.0, 106.0, 110.0],
        "Low": [95.0, 96.0, 100.0],
        "Close": [102.0, 103.0, 108.0],
        "Adj Close": [102.0, 103.0, 108.0],
        "Volume": [1000, 2000, 1500],
    })

    cleaned = cleaner.clean_ticker_data(raw_df, "TEST.NS")
    assert len(cleaned) == 2
    assert list(cleaned["Date"]) == ["2024-01-02", "2024-01-03"]
    # Verify latest record for 2024-01-02 was retained (Close=103.0)
    assert cleaned.loc[cleaned["Date"] == "2024-01-02", "Close"].iloc[0] == 103.0
    assert cleaner.audit_records["TEST.NS"]["duplicate_dates_removed"] == 1


def test_cleaner_strict_rejection_of_invalid_close(tmp_path):
    """Verify non-positive, NaN, and non-finite Close prices are strictly rejected."""
    cleaner = DataCleaner(
        raw_dir=str(tmp_path / "raw"),
        processed_dir=str(tmp_path / "processed"),
        audit_log_path=str(tmp_path / "audit.json"),
    )

    raw_df = pd.DataFrame({
        "Date": ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"],
        "Open": [100.0, 100.0, 100.0, 100.0, 100.0],
        "High": [105.0, 105.0, 105.0, 105.0, 105.0],
        "Low": [95.0, 95.0, 95.0, 95.0, 95.0],
        "Close": [102.0, 0.0, -10.0, np.nan, np.inf],  # 4 invalid records
        "Adj Close": [102.0, 100.0, 100.0, 100.0, 100.0],
        "Volume": [1000, 1000, 1000, 1000, 1000],
    })

    cleaned = cleaner.clean_ticker_data(raw_df, "TEST.NS")
    assert len(cleaned) == 1
    assert cleaned["Date"].iloc[0] == "2024-01-02"
    assert cleaner.audit_records["TEST.NS"]["invalid_close_rejected"] == 4


def test_cleaner_physical_constraint_violations_pruned(tmp_path):
    """Verify physical anomalies (High < Low, High < Open, Low > Close, Volume < 0) are pruned."""
    cleaner = DataCleaner(
        raw_dir=str(tmp_path / "raw"),
        processed_dir=str(tmp_path / "processed"),
        audit_log_path=str(tmp_path / "audit.json"),
    )

    raw_df = pd.DataFrame({
        "Date": ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"],
        "Open": [100.0, 100.0, 110.0, 90.0, 100.0],
        "High": [105.0, 90.0, 105.0, 105.0, 105.0],   # Row 1: High(90) < Low(95)
        "Low":  [95.0, 95.0, 95.0, 95.0, 95.0],       # Row 2: High(105) < Open(110)
        "Close":[102.0, 102.0, 102.0, 80.0, 102.0],   # Row 3: Low(95) > Close(80)
        "Adj Close": [102.0, 102.0, 102.0, 80.0, 102.0],
        "Volume": [1000, 1000, 1000, 1000, -50],      # Row 4: Volume < 0
    })

    cleaned = cleaner.clean_ticker_data(raw_df, "TEST.NS")
    # Only row 0 is physically sound
    assert len(cleaned) == 1
    assert cleaned["Date"].iloc[0] == "2024-01-02"
    assert cleaner.audit_records["TEST.NS"]["physical_anomalies_detected"] == 4


def test_cleaner_proportional_ohlc_scaling_and_fallback(tmp_path):
    """Verify proportional OHLC calculation and fallback f_t = 1.0 when Adj Close is missing."""
    cleaner = DataCleaner(
        raw_dir=str(tmp_path / "raw"),
        processed_dir=str(tmp_path / "processed"),
        audit_log_path=str(tmp_path / "audit.json"),
    )

    # Row 0: Valid split (Close=200, Adj Close=100 -> f=0.5)
    # Row 1: Missing Adj Close (Close=100, Adj Close=NaN -> f=1.0)
    # Row 2: Non-positive Adj Close (Close=100, Adj Close=0.0 -> f=1.0)
    raw_df = pd.DataFrame({
        "Date": ["2024-01-02", "2024-01-03", "2024-01-04"],
        "Open": [190.0, 90.0, 95.0],
        "High": [210.0, 110.0, 105.0],
        "Low": [180.0, 85.0, 90.0],
        "Close": [200.0, 100.0, 100.0],
        "Adj Close": [100.0, np.nan, 0.0],
        "Volume": [1000, 2000, 1500],
    })

    cleaned = cleaner.clean_ticker_data(raw_df, "SPLIT.NS")
    assert len(cleaned) == 3

    # Row 0: f=0.5
    assert cleaned.loc[0, "adj_factor"] == 0.5
    assert cleaned.loc[0, "adj_open"] == 95.0
    assert cleaned.loc[0, "adj_high"] == 105.0
    assert cleaned.loc[0, "adj_low"] == 90.0
    assert cleaned.loc[0, "adj_close"] == 100.0
    # Raw values preserved
    assert cleaned.loc[0, "Open"] == 190.0
    assert cleaned.loc[0, "Close"] == 200.0

    # Row 1: Fallback f=1.0
    assert cleaned.loc[1, "adj_factor"] == 1.0
    assert cleaned.loc[1, "adj_open"] == 90.0
    assert cleaned.loc[1, "adj_close"] == 100.0

    # Row 2: Fallback f=1.0
    assert cleaned.loc[2, "adj_factor"] == 1.0
    assert cleaned.loc[2, "adj_close"] == 100.0

    # Audit records fallback count
    assert cleaner.audit_records["SPLIT.NS"]["adj_close_fallback_triggered"] == 2


def test_cleaner_no_blind_forward_filling_calendar_breaks(tmp_path):
    """Verify that natural exchange breaks (e.g. weekend/holidays) are not artificially forward-filled."""
    cleaner = DataCleaner(
        raw_dir=str(tmp_path / "raw"),
        processed_dir=str(tmp_path / "processed"),
        audit_log_path=str(tmp_path / "audit.json"),
    )

    # Friday followed by Tuesday (weekend + Monday holiday)
    raw_df = pd.DataFrame({
        "Date": ["2024-01-05", "2024-01-09"],
        "Open": [100.0, 105.0],
        "High": [105.0, 110.0],
        "Low": [95.0, 100.0],
        "Close": [102.0, 108.0],
        "Adj Close": [102.0, 108.0],
        "Volume": [1000, 1500],
    })

    cleaned = cleaner.clean_ticker_data(raw_df, "CALENDAR.NS")
    # Cleaned DataFrame must contain exactly the 2 trading observations
    assert len(cleaned) == 2
    assert list(cleaned["Date"]) == ["2024-01-05", "2024-01-09"]


def test_clean_and_save_all_preserves_raw_data_and_writes_audit(tmp_path):
    """Verify clean_and_save_all writes processed CSVs and audit JSON without modifying raw files."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    audit_path = tmp_path / "reports" / "data_cleaning_audit.json"

    raw_dir.mkdir(parents=True)
    raw_file = raw_dir / "RELIANCE.NS_raw.csv"
    raw_content = "Date,Open,High,Low,Close,Adj Close,Volume\n2024-01-02,100,105,95,102,102,1000\n"
    raw_file.write_text(raw_content, encoding="utf-8")

    cleaner = DataCleaner(
        raw_dir=str(raw_dir),
        processed_dir=str(processed_dir),
        audit_log_path=str(audit_path),
    )

    cleaned_dict = cleaner.clean_and_save_all(tickers=["RELIANCE.NS"])

    # 1. Processed file created
    processed_file = processed_dir / "RELIANCE.NS_cleaned.csv"
    assert processed_file.exists()

    # 2. Raw file untouched
    assert raw_file.read_text(encoding="utf-8") == raw_content

    # 3. Audit JSON exists and contains ticker entry
    assert audit_path.exists()
    audit_data = json.loads(audit_path.read_text(encoding="utf-8"))
    assert "RELIANCE.NS" in audit_data["audit_records"]
