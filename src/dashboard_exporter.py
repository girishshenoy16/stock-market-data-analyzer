"""Dashboard Data Exporter Module for Stock Market Data Analyzer.

Compiles single-source-of-truth engineered datasets and master summary metrics
into docs/dashboard_data.js adhering strictly to the frozen versioned schema.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import DEFAULT_INSTRUMENTS

logger = logging.getLogger(__name__)


class DashboardExporter:
    """Exports processed financial datasets to JavaScript bundle for static web delivery."""

    def __init__(
        self,
        processed_dir: str = "data/processed",
        docs_dir: str = "docs",
    ) -> None:
        self.processed_dir = Path(processed_dir)
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.output_js_path = self.docs_dir / "dashboard_data.js"

    @staticmethod
    def sanitize_series(series: pd.Series) -> List[Any]:
        """Convert a pandas Series to a JSON-compliant list with None for NaN/Inf."""
        values = series.values
        result = []
        for v in values:
            if pd.isna(v) or not np.isfinite(v):
                result.append(None)
            elif isinstance(v, (np.floating, float)):
                result.append(round(float(v), 4))
            elif isinstance(v, (np.integer, int)):
                result.append(int(v))
            elif isinstance(v, (np.bool_, bool)):
                result.append(bool(v))
            else:
                result.append(v)
        return result

    def export(
        self,
        instruments: Optional[List[str]] = None,
        benchmark: str = "^NSEI",
    ) -> Path:
        """Compile and write docs/dashboard_data.js adhering to schema."""
        tickers = instruments or DEFAULT_INSTRUMENTS

        # 1. Load Summary Metrics
        summary_path = self.processed_dir / "market_summary_metrics.csv"
        if not summary_path.exists():
            raise FileNotFoundError(f"Summary metrics table missing: {summary_path}")

        summary_df = pd.read_csv(summary_path)
        # Convert records and ensure all NaNs become None for valid JSON serialization
        raw_records = summary_df.to_dict(orient="records")
        summary_metrics = [
            {k: (None if pd.isna(v) else v) for k, v in row.items()}
            for row in raw_records
        ]

        # 2. Load Engineered Datasets & Assemble Instruments Data
        instruments_data: Dict[str, Dict[str, List[Any]]] = {}
        normalization_metadata: Dict[str, Dict[str, Any]] = {}
        record_counts: Dict[str, int] = {}
        first_observations: List[str] = []
        last_observations: List[str] = []

        # Return series for joint correlation matrix
        returns_dict: Dict[str, pd.Series] = {}

        for ticker in tickers:
            eng_path = self.processed_dir / f"{ticker}_engineered.csv"
            if not eng_path.exists():
                raise FileNotFoundError(f"Engineered dataset missing: {eng_path}")

            df = pd.read_csv(eng_path)
            record_counts[ticker] = len(df)
            first_obs = str(df["Date"].iloc[0])
            last_obs = str(df["Date"].iloc[-1])
            first_observations.append(first_obs)
            last_observations.append(last_obs)

            # Record normalization metadata
            base_price = float(df["adj_close"].iloc[0])
            cal_years = (pd.to_datetime(last_obs) - pd.to_datetime(first_obs)).days / 365.25
            normalization_metadata[ticker] = {
                "start_date": first_obs,
                "base_price": round(base_price, 2),
                "calendar_duration_years": round(cal_years, 4),
                "trading_return_intervals": int(len(df["daily_return"].dropna())),
            }

            returns_dict[ticker] = df.set_index("Date")["daily_return"].dropna()

            # Assemble instrument time-series fields
            instruments_data[ticker] = {
                "dates": df["Date"].tolist(),
                "open": self.sanitize_series(df["Open"]),
                "high": self.sanitize_series(df["High"]),
                "low": self.sanitize_series(df["Low"]),
                "close": self.sanitize_series(df["Close"]),
                "adj_open": self.sanitize_series(df["adj_open"]),
                "adj_high": self.sanitize_series(df["adj_high"]),
                "adj_low": self.sanitize_series(df["adj_low"]),
                "adj_close": self.sanitize_series(df["adj_close"]),
                "volume": self.sanitize_series(df["Volume"]),
                "volume_sma_20": self.sanitize_series(df["volume_sma_20"]),
                "volume_spike_ratio": self.sanitize_series(df["volume_spike_ratio"]),
                "rolling_52w_high": self.sanitize_series(df["rolling_52w_high"]),
                "rolling_52w_low": self.sanitize_series(df["rolling_52w_low"]),
                "daily_return": self.sanitize_series(df["daily_return"]),
                "log_return": self.sanitize_series(df["log_return"]),
                "cumulative_return": self.sanitize_series(df["cumulative_return"]),
                "normalized_price": self.sanitize_series(df["normalized_price"]),
                "sma_20": self.sanitize_series(df["sma_20"]),
                "sma_50": self.sanitize_series(df["sma_50"]),
                "sma_200": self.sanitize_series(df["sma_200"]),
                "ema_20": self.sanitize_series(df["ema_20"]),
                "rsi_14": self.sanitize_series(df["rsi_14"]),
                "bb_upper": self.sanitize_series(df["bb_upper"]),
                "bb_middle": self.sanitize_series(df["bb_middle"]),
                "bb_lower": self.sanitize_series(df["bb_lower"]),
                "drawdown": self.sanitize_series(df["drawdown"]),
                "rolling_vol_30d": self.sanitize_series(df["rolling_vol_30d"]),
                "golden_cross_event": self.sanitize_series(df["golden_cross_event"]),
                "death_cross_event": self.sanitize_series(df["death_cross_event"]),
                "bullish_regime": [bool(x) if pd.notna(x) else False for x in df["bullish_regime"]],
            }

        # 3. Precompute Multi-Horizon Period Metrics (5Y, 3Y, 1Y, YTD)
        period_metrics: Dict[str, Dict[str, Dict[str, Any]]] = {
            "5Y": {},
            "3Y": {},
            "1Y": {},
            "YTD": {},
        }
        trading_days_per_year = 252
        daily_rf = (1.0 + 0.065) ** (1.0 / 252.0) - 1.0

        actual_last_date = pd.to_datetime(max(last_observations))
        bench_df = pd.read_csv(self.processed_dir / f"{benchmark}_engineered.csv")
        bench_df["dt"] = pd.to_datetime(bench_df["Date"])

        for period_key in ["5Y", "3Y", "1Y", "YTD"]:
            if period_key == "5Y":
                b_sub = bench_df.copy()
            elif period_key == "3Y":
                cutoff = actual_last_date - pd.DateOffset(years=3)
                b_sub = bench_df[bench_df["dt"] >= cutoff].copy()
            elif period_key == "1Y":
                cutoff = actual_last_date - pd.DateOffset(years=1)
                b_sub = bench_df[bench_df["dt"] >= cutoff].copy()
            elif period_key == "YTD":
                cutoff = pd.Timestamp(year=actual_last_date.year, month=1, day=1)
                b_sub = bench_df[bench_df["dt"] >= cutoff].copy()

            b_returns = b_sub.set_index("Date")["daily_return"].dropna()

            for ticker in tickers:
                t_df = pd.read_csv(self.processed_dir / f"{ticker}_engineered.csv")
                t_df["dt"] = pd.to_datetime(t_df["Date"])

                if period_key == "5Y":
                    t_sub = t_df.copy()
                elif period_key == "3Y":
                    cutoff = actual_last_date - pd.DateOffset(years=3)
                    t_sub = t_df[t_df["dt"] >= cutoff].copy()
                elif period_key == "1Y":
                    cutoff = actual_last_date - pd.DateOffset(years=1)
                    t_sub = t_df[t_df["dt"] >= cutoff].copy()
                elif period_key == "YTD":
                    cutoff = pd.Timestamp(year=actual_last_date.year, month=1, day=1)
                    t_sub = t_df[t_df["dt"] >= cutoff].copy()

                if len(t_sub) >= 2:
                    p_vals = t_sub["adj_close"].values
                    r_vals = t_sub["daily_return"].dropna().values
                    d_vals = t_sub["dt"].values

                    p_start = float(p_vals[0])
                    p_end = float(p_vals[-1])
                    d_start = pd.to_datetime(d_vals[0])
                    d_end = pd.to_datetime(d_vals[-1])

                    cal_years = (d_end - d_start).days / 365.25
                    trading_intervals = len(r_vals)

                    # CAGR
                    if cal_years > 0 and p_start > 0 and p_end > 0:
                        cagr = (p_end / p_start) ** (1.0 / cal_years) - 1.0
                    else:
                        cagr = np.nan

                    # Volatility & Sharpe Ratio
                    if len(r_vals) >= 2 and np.std(r_vals, ddof=1) > 0:
                        ann_vol = float(np.std(r_vals, ddof=1) * np.sqrt(trading_days_per_year))
                        excess = r_vals - daily_rf
                        if np.std(excess, ddof=1) > 0:
                            sharpe = float(np.sqrt(trading_days_per_year) * (np.mean(excess) / np.std(excess, ddof=1)))
                        else:
                            sharpe = np.nan
                    else:
                        ann_vol = np.nan
                        sharpe = np.nan

                    # Maximum Drawdown (Running peak within active period)
                    cum_max = np.maximum.accumulate(p_vals)
                    period_drawdown = (p_vals - cum_max) / cum_max
                    max_dd = float(np.min(period_drawdown))

                    # Historical VaR 95% (5th percentile of daily returns within active period)
                    var_95 = np.percentile(r_vals, 5) if len(r_vals) >= 1 else np.nan

                    # Beta vs Benchmark
                    if ticker == benchmark:
                        beta = 1.0
                    else:
                        t_returns = t_sub.set_index("Date")["daily_return"].dropna()
                        aligned = pd.concat([t_returns, b_returns], axis=1, join="inner").dropna()
                        if len(aligned) >= 30 and aligned.iloc[:, 1].var(ddof=1) > 0:
                            cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1], ddof=1)
                            var_bmk = aligned.iloc[:, 1].var(ddof=1)
                            beta = float(cov / var_bmk)
                        else:
                            beta = np.nan

                    # Fixed definitions preserved
                    last_close = float(p_vals[-1])
                    w52_h = float(t_sub["rolling_52w_high"].iloc[-1]) if ("rolling_52w_high" in t_sub and pd.notna(t_sub["rolling_52w_high"].iloc[-1])) else None
                    w52_l = float(t_sub["rolling_52w_low"].iloc[-1]) if ("rolling_52w_low" in t_sub and pd.notna(t_sub["rolling_52w_low"].iloc[-1])) else None

                    period_metrics[period_key][ticker] = {
                        "ticker": ticker,
                        "period": period_key,
                        "cagr_pct": round(cagr * 100.0, 4) if pd.notna(cagr) else None,
                        "annualized_volatility_pct": round(ann_vol * 100.0, 4) if pd.notna(ann_vol) else None,
                        "sharpe_ratio": round(sharpe, 4) if pd.notna(sharpe) else None,
                        "max_drawdown_pct": round(max_dd * 100.0, 4) if pd.notna(max_dd) else None,
                        "var_95_pct": round(float(var_95) * 100.0, 4) if pd.notna(var_95) else None,
                        "beta_nifty": round(beta, 4) if pd.notna(beta) else None,
                        "last_close": round(last_close, 2) if pd.notna(last_close) else None,
                        "52w_high": round(w52_h, 2) if w52_h is not None else None,
                        "52w_low": round(w52_l, 2) if w52_l is not None else None,
                        "calendar_duration_years": round(cal_years, 4) if cal_years > 0 else None,
                        "trading_return_intervals": trading_intervals,
                        "start_date": str(d_start.date()),
                        "end_date": str(d_end.date()),
                    }
                else:
                    period_metrics[period_key][ticker] = {
                        "ticker": ticker,
                        "period": period_key,
                        "cagr_pct": None,
                        "annualized_volatility_pct": None,
                        "sharpe_ratio": None,
                        "max_drawdown_pct": None,
                        "var_95_pct": None,
                        "beta_nifty": 1.0 if ticker == benchmark else None,
                        "last_close": None,
                        "52w_high": None,
                        "52w_low": None,
                        "calendar_duration_years": None,
                        "trading_return_intervals": 0,
                        "start_date": None,
                        "end_date": None,
                    }

        # 4. Correlation Matrix (complete-case joint return alignment)
        joint_returns = pd.DataFrame(returns_dict).dropna()
        corr_matrix_df = joint_returns.corr(method="pearson")
        corr_symbols = list(corr_matrix_df.columns)
        corr_matrix_values = [
            [round(float(val), 4) for val in row] for row in corr_matrix_df.values
        ]

        # 5. Global Metadata
        actual_first = min(first_observations)
        actual_last = max(last_observations)
        pipeline_exec = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload: Dict[str, Any] = {
            "metadata": {
                "schema_version": "1.0.0",
                "methodology_version": "2026.1",
                "pipeline_execution_timestamp": pipeline_exec,
                "market_data_last_observation_date": actual_last,
                "date_range": {
                    "requested_start": "2021-09-28",
                    "requested_end": "2026-09-28",
                    "actual_first_observation": actual_first,
                    "actual_last_observation": actual_last,
                },
                "instruments": tickers,
                "benchmark_symbol": benchmark,
                "price_basis": {
                    "returns_and_indicators": "Effective Adjusted Close (Adj Close, fallback to Close with warning)",
                    "candlesticks": "Proportionally Adjusted OHLC via factor (Adj Close / Close, fallback f=1.0 with raw Open/High/Low/Close)",
                    "rolling_52w_high_low": "Adjusted price basis (fixed rolling 252-day window, min_periods=252, first 251 observations NaN)",
                    "raw_ohlc": "Unadjusted Open, High, Low, Close retained for reference",
                },
                "provenance_reference": "data/processed/{TICKER}_engineered.csv (Local provenance only)",
                "risk_free_proxy": {
                    "annual_rate": 0.065,
                    "daily_conversion_formula": "(1 + 0.065)**(1/252) - 1",
                    "daily_rate": 0.000250007,
                    "description": "Illustrative proxy assumption representing 10-Yr Indian G-Sec yield",
                },
                "normalization_metadata": normalization_metadata,
                "record_counts": record_counts,
            },
            "summary_metrics": summary_metrics,
            "period_metrics": period_metrics,
            "correlation_matrix": {
                "symbols": corr_symbols,
                "matrix": corr_matrix_values,
            },
            "instruments_data": instruments_data,
        }

        # 5. Serialize into docs/dashboard_data.js via atomic write
        json_str = json.dumps(payload, indent=2)
        js_content = f"// Stock Market Data Analyzer - Precomputed Dashboard Dataset\n// Schema Version: 1.0.0 | Methodology: 2026.1\nwindow.STOCK_DASHBOARD_DATA = {json_str};\n"

        temp_path = self.output_js_path.with_name(f"{self.output_js_path.name}.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(js_content)
            temp_path.replace(self.output_js_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        file_size_kb = self.output_js_path.stat().st_size / 1024.0
        logger.info(
            "Successfully compiled and saved %s (%.1f KB)",
            self.output_js_path,
            file_size_kb,
        )
        return self.output_js_path


if __name__ == "__main__":
    from src.logger import setup_logging
    setup_logging()
    exporter = DashboardExporter()
    out_file = exporter.export()
    print(f"\nDashboard data export completed: {out_file}")
