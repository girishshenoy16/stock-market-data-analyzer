"""Data Loader Module for Stock Market Data Analyzer.

Handles downloading historical OHLCV market data from Yahoo Finance,
normalizing MultiIndex schemas, creating immutable timestamped archives,
and validating market data freshness against the trading calendar.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import yfinance as yf

# Module logger (inherits centralized configuration from src.logger)
logger = logging.getLogger(__name__)

# Default Asset Universe & Date Horizon
DEFAULT_INSTRUMENTS: List[str] = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "SBIN.NS",
    "ICICIBANK.NS",
    "^NSEI",
]
DEFAULT_START_DATE: str = "2021-09-28"
DEFAULT_END_DATE: str = "2026-09-28"
EXPECTED_COLUMNS: List[str] = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


class StockDataLoader:
    """Manages downloading, archival, and validation of equity market data."""

    def __init__(
        self,
        raw_dir: str = "data/raw",
        archive_dir: str = "data/raw/archive",
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.archive_dir = Path(archive_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def flatten_columns(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Flatten MultiIndex column headers from yfinance into standardized single-level names.

        Args:
            df: Raw DataFrame downloaded from yfinance.
            ticker: Ticker symbol being processed.

        Returns:
            DataFrame with normalized single-level column headers and ISO Date column.
        """
        data = df.copy()

        # Handle MultiIndex columns produced by modern yfinance
        if isinstance(data.columns, pd.MultiIndex):
            # Often columns are (PriceType, Ticker) or (Ticker, PriceType)
            level_0 = [str(c[0]).strip() for c in data.columns]
            level_1 = [str(c[1]).strip() for c in data.columns]

            # Check which level matches expected price fields
            price_fields = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
            if set(level_0).intersection(price_fields):
                data.columns = pd.Index(level_0)
            elif set(level_1).intersection(price_fields):
                data.columns = pd.Index(level_1)
            else:
                data.columns = pd.Index([f"{c[0]}_{c[1]}".strip("_") for c in data.columns])

        # Reset index if Date is the index
        if "Date" not in data.columns:
            if isinstance(data.index, pd.DatetimeIndex):
                data = data.reset_index()
            elif "Date" in data.index.names:
                data = data.reset_index()

        # Ensure Date column exists and format as YYYY-MM-DD
        if "Date" in data.columns:
            data["Date"] = pd.to_datetime(data["Date"]).dt.strftime("%Y-%m-%d")
        else:
            raise ValueError(f"No Date column or DatetimeIndex found for ticker {ticker}.")

        # Check for presence of required columns
        missing = [c for c in EXPECTED_COLUMNS if c not in data.columns]
        if missing:
            raise ValueError(f"Ticker {ticker} DataFrame is missing required columns: {missing}")

        # Retain only expected columns and ensure chronological ordering
        data = data[EXPECTED_COLUMNS].copy()
        data = data.sort_values("Date").reset_index(drop=True)
        return data

    @staticmethod
    def check_staleness(
        last_obs_date_str: str,
        current_dt: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Validate latest observation against expected weekday market activity.

        Args:
            last_obs_date_str: ISO string of latest observation date.
            current_dt: Current datetime (defaults to current system time).

        Returns:
            Dictionary with staleness assessment details.
        """
        now = current_dt or datetime.now()
        last_obs_date = datetime.strptime(last_obs_date_str, "%Y-%m-%d").date()
        current_date = now.date()
        diff_days = (current_date - last_obs_date).days

        # Market is closed on weekends (Saturday=5, Sunday=6)
        # If today is Monday, last trading day is typically Friday (diff=3 days)
        # If diff > 4 calendar days, flag as potentially stale data feed
        is_stale = False
        warning_msg = None

        if diff_days < 0:
            warning_msg = f"Latest observation date {last_obs_date_str} is in the future relative to system date {current_date}."
            is_stale = True
        elif diff_days > 4:
            warning_msg = (
                f"Data may be stale: Latest observation is {last_obs_date_str} ({diff_days} days ago). "
                "Verify if exchange holiday or feed lag is present."
            )
            is_stale = True

        if warning_msg:
            logger.warning("[%s] %s", last_obs_date_str, warning_msg)

        return {
            "market_data_last_observation_date": last_obs_date_str,
            "system_current_date": str(current_date),
            "calendar_gap_days": diff_days,
            "staleness_flag": is_stale,
            "warning": warning_msg,
        }

    def save_and_archive(self, df: pd.DataFrame, ticker: str, timestamp_str: str) -> Dict[str, Path]:
        """Save active raw CSV and immutable versioned snapshot.

        Args:
            df: Normalized DataFrame.
            ticker: Ticker symbol.
            timestamp_str: Timestamp string for archival filename.

        Returns:
            Dictionary containing active and archive file paths.
        """
        active_path = self.raw_dir / f"{ticker}_raw.csv"
        archive_path = self.archive_dir / f"{ticker}_raw_{timestamp_str}.csv"

        df.to_csv(active_path, index=False)
        df.to_csv(archive_path, index=False)

        logger.info("Saved raw snapshot: %s", active_path)
        logger.info("Archived immutable snapshot: %s", archive_path)

        return {"active": active_path, "archive": archive_path}

    def fetch_ticker(
        self,
        ticker: str,
        start_date: str = DEFAULT_START_DATE,
        end_date: str = DEFAULT_END_DATE,
        timestamp_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Download single instrument data, normalize, archive, and validate freshness.

        Args:
            ticker: Yahoo Finance ticker symbol.
            start_date: Inclusive start date (YYYY-MM-DD).
            end_date: Exclusive end date (YYYY-MM-DD).
            timestamp_str: Optional timestamp for archive naming.

        Returns:
            Dictionary containing metadata and the processed raw DataFrame.
        """
        ts = timestamp_str or datetime.now().strftime("%Y%m%d_%H%M%S")
        exec_timestamp = datetime.now(timezone.utc).isoformat()

        logger.info("Downloading ticker %s (%s to %s)...", ticker, start_date, end_date)
        raw_download = yf.download(
            tickers=ticker,
            start=start_date,
            end=end_date,
            auto_adjust=False,
            progress=False,
        )

        if raw_download.empty:
            raise RuntimeError(f"Download returned empty DataFrame for ticker {ticker}.")

        normalized_df = self.flatten_columns(raw_download, ticker)
        paths = self.save_and_archive(normalized_df, ticker, ts)

        first_obs = normalized_df["Date"].iloc[0]
        last_obs = normalized_df["Date"].iloc[-1]
        ref_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        staleness = self.check_staleness(last_obs, current_dt=ref_dt)

        metadata = {
            "ticker": ticker,
            "pipeline_execution_timestamp": exec_timestamp,
            "market_data_last_observation_date": last_obs,
            "first_observation_date": first_obs,
            "record_count": len(normalized_df),
            "active_file": str(paths["active"]),
            "archive_file": str(paths["archive"]),
            "staleness_details": staleness,
        }
        return {"data": normalized_df, "metadata": metadata}

    def download_all(
        self,
        tickers: Optional[List[str]] = None,
        start_date: str = DEFAULT_START_DATE,
        end_date: str = DEFAULT_END_DATE,
    ) -> Dict[str, Dict[str, Any]]:
        """Download all universe instruments sequentially with archival and verification.

        Args:
            tickers: List of tickers to download.
            start_date: Historical start date.
            end_date: Historical end date.

        Returns:
            Dictionary mapping each ticker to its result metadata and DataFrame.
        """
        instruments = tickers or DEFAULT_INSTRUMENTS
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results: Dict[str, Dict[str, Any]] = {}

        logger.info("Starting ingestion for %d instruments: %s", len(instruments), instruments)
        for ticker in instruments:
            try:
                res = self.fetch_ticker(ticker, start_date, end_date, timestamp_str=ts)
                results[ticker] = res
                logger.info(
                    "Successfully ingested %s: %d records [%s to %s]",
                    ticker,
                    res["metadata"]["record_count"],
                    res["metadata"]["first_observation_date"],
                    res["metadata"]["market_data_last_observation_date"],
                )
            except Exception as e:
                logger.error("Failed downloading %s: %s", ticker, e)
                raise

        logger.info("All %d instruments downloaded and archived successfully.", len(results))
        return results


if __name__ == "__main__":
    from src.logger import setup_logging
    setup_logging()
    loader = StockDataLoader()
    results = loader.download_all()
    print("Ingestion complete. Summary:")
    for ticker, res in results.items():
        meta = res["metadata"]
        print(f"  - {ticker}: {meta['record_count']} rows, Last: {meta['market_data_last_observation_date']}")
