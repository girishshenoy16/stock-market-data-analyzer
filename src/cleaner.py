"""Data Cleaner Module for Stock Market Data Analyzer.

Implements rigorous financial data sanitization, deduplication,
physical OHLCV relationship validation, strict Close rejection,
trading calendar awareness without blind fills, proportional
candlestick adjustment scaling, and data quality audit logging.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataCleaner:
    """Sanitizes raw stock market datasets according to strict financial data engineering standards."""

    def __init__(
        self,
        raw_dir: str = "data/raw",
        processed_dir: str = "data/processed",
        audit_log_path: str = "outputs/reports/data_cleaning_audit.json",
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.audit_log_path = Path(audit_log_path)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_records: Dict[str, Any] = {}

    def clean_ticker_data(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Sanitize a raw equity dataset.

        Args:
            df: Raw DataFrame containing Date, Open, High, Low, Close, Adj Close, Volume.
            ticker: Symbol name for logging and auditing.

        Returns:
            Cleaned DataFrame with proportional OHLC fields and verified physical constraints.
        """
        audit: Dict[str, Any] = {
            "ticker": ticker,
            "initial_rows": len(df),
            "duplicate_dates_removed": 0,
            "invalid_close_rejected": 0,
            "physical_anomalies_detected": 0,
            "adj_close_fallback_triggered": 0,
            "zero_volume_days": 0,
            "weekday_gaps": [],
            "cleaned_rows": 0,
        }

        data = df.copy()

        # 1. Deduplication & Chronological Normalization
        initial_count = len(data)
        data = data.drop_duplicates(subset=["Date"], keep="last")
        audit["duplicate_dates_removed"] = initial_count - len(data)

        # Ensure Date is monotonic ISO string without timezone
        data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None).dt.strftime("%Y-%m-%d")
        data = data.sort_values("Date").reset_index(drop=True)

        # 2. Strict Rejection Policy for Invalid Close
        close_numeric = pd.to_numeric(data["Close"], errors="coerce")
        valid_close_mask = close_numeric.notna() & np.isfinite(close_numeric) & (close_numeric > 0)
        invalid_close_count = int((~valid_close_mask).sum())
        if invalid_close_count > 0:
            logger.warning(
                "[%s] Rejecting %d records with non-positive or invalid Close.",
                ticker,
                invalid_close_count,
            )
            data = data[valid_close_mask].copy()
        audit["invalid_close_rejected"] = invalid_close_count

        # Convert core OHLCV columns to numeric
        for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            data[col] = pd.to_numeric(data[col], errors="coerce")

        # Re-check for any rows where core prices became NaN
        essential_mask = data[["Open", "High", "Low", "Close"]].notna().all(axis=1)
        data = data[essential_mask].copy()

        # 3. Physical OHLCV Relationship Checks
        high_low_violation = data["High"] < data["Low"]
        high_open_close_violation = (data["High"] < data["Open"]) | (data["High"] < data["Close"])
        low_open_close_violation = (data["Low"] > data["Open"]) | (data["Low"] > data["Close"])
        neg_volume = data["Volume"] < 0

        anomalies_mask = high_low_violation | high_open_close_violation | low_open_close_violation | neg_volume
        anomaly_count = int(anomalies_mask.sum())
        audit["physical_anomalies_detected"] = anomaly_count

        if anomaly_count > 0:
            logger.warning(
                "[%s] Detected %d physical OHLCV relationship anomalies; pruning corrupted rows.",
                ticker,
                anomaly_count,
            )
            data = data[~anomalies_mask].copy()

        # Check for zero volume days (common in benchmark index, rare in stocks)
        zero_vol = int((data["Volume"] <= 0).sum())
        audit["zero_volume_days"] = zero_vol

        # Check for weekday gaps > 4 calendar days (long holidays or feed pauses)
        dates = pd.to_datetime(data["Date"])
        day_diffs = dates.diff().dt.days
        gap_rows = data[day_diffs > 4]
        for _, row in gap_rows.iterrows():
            audit["weekday_gaps"].append(
                {"date": row["Date"], "gap_days": int(day_diffs.loc[_])}
            )

        # 4. Proportional OHLC Scaling & Fallback Logic
        adj_close = data["Adj Close"]
        raw_close = data["Close"]

        # Valid Adj Close mask: notna, finite, positive
        valid_adj = adj_close.notna() & np.isfinite(adj_close) & (adj_close > 0)
        fallback_mask = ~valid_adj
        fallback_count = int(fallback_mask.sum())
        audit["adj_close_fallback_triggered"] = fallback_count

        if fallback_count > 0:
            logger.warning(
                "[%s] Adj Close invalid or non-positive on %d records; applying fallback factor f_t=1.0.",
                ticker,
                fallback_count,
            )

        # Compute factor f_t
        adj_factor = np.where(valid_adj, adj_close / raw_close, 1.0)
        data["adj_factor"] = adj_factor

        # Proportionally adjusted OHLC
        data["adj_open"] = data["Open"] * adj_factor
        data["adj_high"] = data["High"] * adj_factor
        data["adj_low"] = data["Low"] * adj_factor
        data["adj_close"] = np.where(valid_adj, data["Adj Close"], data["Close"])

        data = data.reset_index(drop=True)
        audit["cleaned_rows"] = len(data)
        self.audit_records[ticker] = audit

        return data

    def clean_and_save_all(
        self,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Clean all active raw datasets and write to processed directory."""
        from src.data_loader import DEFAULT_INSTRUMENTS

        instruments = tickers or DEFAULT_INSTRUMENTS
        cleaned_dict: Dict[str, pd.DataFrame] = {}

        logger.info("Starting cleaning for %d instruments: %s", len(instruments), instruments)

        for ticker in instruments:
            raw_path = self.raw_dir / f"{ticker}_raw.csv"
            if not raw_path.exists():
                raise FileNotFoundError(f"Raw file not found: {raw_path}")

            raw_df = pd.read_csv(raw_path)
            cleaned_df = self.clean_ticker_data(raw_df, ticker)

            out_path = self.processed_dir / f"{ticker}_cleaned.csv"
            cleaned_df.to_csv(out_path, index=False)
            logger.info("Saved cleaned dataset: %s (%d records)", out_path, len(cleaned_df))
            cleaned_dict[ticker] = cleaned_df

        # Save cumulative audit log
        with open(self.audit_log_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.now().isoformat(),
                    "audit_records": self.audit_records,
                },
                f,
                indent=2,
            )
        logger.info("Data cleaning audit report written to %s", self.audit_log_path)

        return cleaned_dict


if __name__ == "__main__":
    from src.logger import setup_logging
    setup_logging()
    cleaner = DataCleaner()
    cleaned = cleaner.clean_and_save_all()
    print("Cleaning complete. Processed files:")
    for ticker, df in cleaned.items():
        print(f"  - {ticker}: {len(df)} rows, adj_close min={df['adj_close'].min():.2f}, max={df['adj_close'].max():.2f}")
