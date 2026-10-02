"""Live Network Integration Tests for Yahoo Finance Ingestion.

Isolated from the default offline test suite. Requires active internet connectivity.
Enabled only when environment variable RUN_LIVE_TESTS=1 is set.
"""

import os
from pathlib import Path
import sys
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yfinance as yf
from src.data_loader import DEFAULT_INSTRUMENTS, StockDataLoader

LIVE_ENABLED = os.environ.get("RUN_LIVE_TESTS") == "1"


@pytest.mark.skipif(not LIVE_ENABLED, reason="Live network tests require RUN_LIVE_TESTS=1 (isolated from offline suite)")
def test_live_yfinance_connectivity():
    """Verify live network retrieval and parsing of 5-day sample from Yahoo Finance."""
    ticker = "RELIANCE.NS"
    data = yf.download(ticker, period="5d", auto_adjust=False, progress=False)

    assert not data.empty, f"Live download for {ticker} returned empty DataFrame"
    loader = StockDataLoader()
    flattened = loader.flatten_columns(data, ticker)

    assert len(flattened) >= 1
    assert set(["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]).issubset(set(flattened.columns))
    assert flattened["Close"].iloc[-1] > 0
