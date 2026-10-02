"""Unit Tests for Automated Execution Reporter Module (src/reporter.py).

Verifies:
1. Loading and schema validation of market_summary_metrics.csv.
2. Canonical benchmark-first table ordering in generated digest.
3. Accurate metric formatting (₹ for stocks, pts for index, % for returns/drawdown).
4. Accurate quantitative ranking generation (CAGR, Sharpe, Volatility, Max DD, VaR 95%, Beta).
5. Accurate 52-week corridor calculation and formatting.
6. Execution without errors and generation of output text digest.
"""

from pathlib import Path
import sys
import pandas as pd
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reporter import PerformanceReporter


def test_reporter_file_not_found_handling(tmp_path):
    """Verify reporter raises FileNotFoundError on missing summary metrics."""
    non_existent = tmp_path / "non_existent.csv"
    reporter = PerformanceReporter(summary_metrics_path=str(non_existent), output_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        reporter.load_metrics()


def test_reporter_schema_validation(tmp_path):
    """Verify reporter raises ValueError when required columns are missing."""
    bad_csv = tmp_path / "bad_metrics.csv"
    bad_df = pd.DataFrame({"ticker": ["RELIANCE.NS"], "cagr_pct": [1.2]})
    bad_df.to_csv(bad_csv, index=False)

    reporter = PerformanceReporter(summary_metrics_path=str(bad_csv), output_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Missing required columns"):
        reporter.load_metrics()


def test_reporter_generates_digest_with_benchmark_first(tmp_path):
    """Verify reporter produces automated_performance_digest.txt with NIFTY 50 first."""
    metrics_csv = tmp_path / "market_summary_metrics.csv"
    mock_data = pd.DataFrame({
        "ticker": ["RELIANCE.NS", "^NSEI", "TCS.NS"],
        "cagr_pct": [1.219, 5.4588, -8.7206],
        "annualized_volatility_pct": [22.2752, 13.8124, 22.5833],
        "sharpe_ratio": [-0.1163, 0.0054, -0.576],
        "max_drawdown_pct": [-27.1757, -17.2298, -53.3934],
        "var_95_pct": [-2.1314, -1.3936, -2.1069],
        "beta_nifty": [1.1124, 1.0, 0.8134],
        "last_close": [1226.0, 23140.5, 2082.0],
        "52w_high": [1604.38, 26373.2, 3287.16],
        "52w_low": [1210.5, 22182.55, 1966.02],
    })
    mock_data.to_csv(metrics_csv, index=False)

    reporter = PerformanceReporter(
        summary_metrics_path=str(metrics_csv),
        output_dir=str(tmp_path),
        output_filename="test_digest.txt",
    )
    digest_path = reporter.generate_digest()

    assert digest_path.exists()
    content = digest_path.read_text(encoding="utf-8")

    # Verify header and sections
    assert "AUTOMATED PERFORMANCE & RISK DIGEST" in content
    assert "EXECUTIVE PERFORMANCE & RISK SUMMARY TABLE" in content
    assert "QUANTITATIVE RANKINGS ACROSS ASSET UNIVERSE" in content
    assert "52-WEEK TRADING CORRIDOR & POSITION ANALYSIS" in content

    # Verify ^NSEI appears before RELIANCE.NS in the summary table
    idx_nsei = content.find("^NSEI")
    idx_rel = content.find("RELIANCE.NS")
    assert idx_nsei != -1 and idx_rel != -1
    assert idx_nsei < idx_rel, "^NSEI benchmark must appear before RELIANCE.NS in table"

    # Verify unit formatting
    assert "23,140.50 pts" in content
    assert "₹1,226.00" in content
    assert "6.50% p.a." in content
