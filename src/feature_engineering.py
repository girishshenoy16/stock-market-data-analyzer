"""Feature Engineering and Financial Analytics Module.

Generates the single-source-of-truth enriched financial datasets,
cross-instrument risk-return metrics, pairwise Beta vs NIFTY 50,
complete-case Pearson correlation matrix, and market_summary_metrics.csv.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import DEFAULT_INSTRUMENTS

logger = logging.getLogger(__name__)

# Core Financial Constants
ANNUAL_RISK_FREE_RATE = 0.065  # 6.5% illustrative proxy for Indian 10-Yr G-Sec
DAILY_RISK_FREE_RATE = (1.0 + ANNUAL_RISK_FREE_RATE) ** (1.0 / 252.0) - 1.0  # ~0.000250007
TRADING_DAYS_PER_YEAR = 252
BENCHMARK_TICKER = "^NSEI"


class FeatureEngineer:
    """Computes technical indicators, risk metrics, and summary tables from cleaned stock data."""

    def __init__(
        self,
        processed_dir: str = "data/processed",
        benchmark_ticker: str = BENCHMARK_TICKER,
    ) -> None:
        self.processed_dir = Path(processed_dir)
        self.benchmark_ticker = benchmark_ticker

    @staticmethod
    def calculate_rsi_14(prices: pd.Series) -> pd.Series:
        """Compute Wilder's Relative Strength Index (RSI - 14) with strict edge-case safeguards.

        Args:
            prices: Effective adjusted close price series.

        Returns:
            RSI series with Wilder's exponential smoothing (alpha=1/14).
        """
        n = len(prices)
        rsi = pd.Series(np.nan, index=prices.index, dtype=float)
        if n < 15:
            return rsi

        delta = prices.diff().values
        gains = np.where(delta > 0, delta, 0.0)
        losses = np.where(delta < 0, -delta, 0.0)

        # Initial 14-period SMA
        avg_gain = np.mean(gains[1:15])
        avg_loss = np.mean(losses[1:15])

        # Compute initial RSI at index 14
        if avg_loss == 0.0 and avg_gain == 0.0:
            rsi.iloc[14] = 50.0
        elif avg_loss == 0.0:
            rsi.iloc[14] = 100.0
        elif avg_gain == 0.0:
            rsi.iloc[14] = 0.0
        else:
            rs = avg_gain / avg_loss
            rsi.iloc[14] = 100.0 - (100.0 / (1.0 + rs))

        # Wilder's Smoothing for t >= 15
        alpha = 1.0 / 14.0
        for t in range(15, n):
            avg_gain = (avg_gain * 13.0 + gains[t]) / 14.0
            avg_loss = (avg_loss * 13.0 + losses[t]) / 14.0

            if avg_loss == 0.0 and avg_gain == 0.0:
                rsi.iloc[t] = 50.0
            elif avg_loss == 0.0:
                rsi.iloc[t] = 100.0
            elif avg_gain == 0.0:
                rsi.iloc[t] = 0.0
            else:
                rs = avg_gain / avg_loss
                rsi.iloc[t] = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    def engineer_instrument(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Compute all single-instrument financial analytics and technical indicators.

        Args:
            df: Cleaned DataFrame for ticker.
            ticker: Symbol name.

        Returns:
            Enriched DataFrame with authoritative feature columns.
        """
        data = df.copy()

        # Effective adjusted close series (with defined fallback if missing)
        if "adj_close" in data.columns and data["adj_close"].notna().any():
            price = data["adj_close"]
        else:
            logger.warning("[%s] adj_close unavailable; falling back to Close.", ticker)
            price = data["Close"]

        # Proportionally adjusted High / Low (fallback to raw if missing)
        adj_high = data["adj_high"] if "adj_high" in data.columns else data["High"]
        adj_low = data["adj_low"] if "adj_low" in data.columns else data["Low"]

        # 1. Returns Engine
        daily_return = price.pct_change()
        data["daily_return"] = daily_return
        data["log_return"] = np.log(price / price.shift(1))
        # Cumulative return: (1 + R).cumprod() - 1, starting from 0.0 at t=0
        data["cumulative_return"] = (1.0 + daily_return.fillna(0.0)).cumprod() - 1.0

        # 2. Normalized Performance from Own First Valid Observation
        base_price = price.iloc[0]
        data["normalized_price"] = (price / base_price) * 100.0

        # 3. Moving Averages & Trend Regimes
        # Warm-up policy: min_periods equals window size; initial periods remain NaN
        data["sma_20"] = price.rolling(window=20, min_periods=20).mean()
        data["sma_50"] = price.rolling(window=50, min_periods=50).mean()
        data["sma_200"] = price.rolling(window=200, min_periods=200).mean()
        data["ema_20"] = price.ewm(span=20, adjust=False).mean()

        # Golden Cross & Death Cross discrete events
        sma50 = data["sma_50"]
        sma200 = data["sma_200"]
        sma50_prev = sma50.shift(1)
        sma200_prev = sma200.shift(1)

        golden_cross = (
            (sma50 > sma200) & (sma50_prev <= sma200_prev) & sma50.notna() & sma200.notna()
        ).astype(int)
        death_cross = (
            (sma50 < sma200) & (sma50_prev >= sma200_prev) & sma50.notna() & sma200.notna()
        ).astype(int)
        bullish_regime = (sma50 > sma200) & sma50.notna() & sma200.notna()

        data["golden_cross_event"] = golden_cross
        data["death_cross_event"] = death_cross
        data["bullish_regime"] = bullish_regime

        # 4. Bollinger Bands (20-day SMA +/- 2*sigma_20 on effective adjusted close)
        sigma_20 = price.rolling(window=20, min_periods=20).std(ddof=1)
        data["bb_middle"] = data["sma_20"]
        data["bb_upper"] = data["sma_20"] + (2.0 * sigma_20)
        data["bb_lower"] = data["sma_20"] - (2.0 * sigma_20)

        # 5. Wilder's RSI - 14
        data["rsi_14"] = self.calculate_rsi_14(price)

        # 6. Risk, Volatility & Drawdown Series
        data["rolling_vol_30d"] = daily_return.rolling(window=30, min_periods=30).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        running_peak = price.cummax()
        data["drawdown"] = (price - running_peak) / running_peak

        # 7. Volume Analytics
        data["volume_sma_20"] = data["Volume"].rolling(window=20, min_periods=20).mean()
        data["volume_spike_ratio"] = np.where(
            data["volume_sma_20"] > 0,
            data["Volume"] / data["volume_sma_20"],
            np.nan,
        )

        # 8. Explicit Adjusted 52-Week High & Low
        # Warm-up policy: Fixed rolling window of 252 observations, min_periods=252.
        # First 251 observations strictly evaluate to NaN.
        data["rolling_52w_high"] = adj_high.rolling(window=252, min_periods=252).max()
        data["rolling_52w_low"] = adj_low.rolling(window=252, min_periods=252).min()

        return data

    def compute_summary_row(
        self,
        df_engineered: pd.DataFrame,
        ticker: str,
        benchmark_returns: pd.Series,
    ) -> Dict[str, Any]:
        """Compute master summary metrics for a single instrument."""
        price = df_engineered["adj_close"]
        returns = df_engineered["daily_return"].dropna()
        dates = pd.to_datetime(df_engineered["Date"])

        # 1. First and last valid points
        p_start = price.iloc[0]
        p_end = price.iloc[-1]
        d_start = dates.iloc[0]
        d_end = dates.iloc[-1]

        calendar_duration_years = (d_end - d_start).days / 365.25
        trading_return_intervals = len(returns)

        # 2. CAGR
        if calendar_duration_years > 0 and p_start > 0 and p_end > 0:
            cagr = (p_end / p_start) ** (1.0 / calendar_duration_years) - 1.0
        else:
            cagr = np.nan

        # 3. Annualized Volatility (ddof=1)
        if len(returns) >= 2 and returns.std(ddof=1) > 0:
            ann_vol = returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
            # 4. Sharpe Ratio (Exact Compounding daily Rf)
            excess_returns = returns - DAILY_RISK_FREE_RATE
            if excess_returns.std(ddof=1) > 0:
                sharpe = np.sqrt(TRADING_DAYS_PER_YEAR) * (excess_returns.mean() / excess_returns.std(ddof=1))
            else:
                sharpe = np.nan
        else:
            ann_vol = np.nan
            sharpe = np.nan

        # 5. Maximum Drawdown
        max_drawdown = df_engineered["drawdown"].min() if "drawdown" in df_engineered else np.nan

        # 6. VaR 95% 1-Day (Empirical 5th percentile)
        var_95 = np.percentile(returns, 5) if len(returns) >= 1 else np.nan

        # 7. 52-Week High & Low (Directly from engineered dataset's latest valid observation)
        w52_high = df_engineered["rolling_52w_high"].iloc[-1] if "rolling_52w_high" in df_engineered else np.nan
        w52_low = df_engineered["rolling_52w_low"].iloc[-1] if "rolling_52w_low" in df_engineered else np.nan
        last_close = price.iloc[-1]

        # 8. Beta vs Benchmark (Pairwise date-aligned)
        if ticker == self.benchmark_ticker:
            beta = 1.0
        else:
            stock_series = df_engineered.set_index("Date")["daily_return"].dropna()
            aligned = pd.concat([stock_series, benchmark_returns], axis=1, join="inner").dropna()
            if len(aligned) >= 30 and aligned.iloc[:, 1].var(ddof=1) > 0:
                cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1], ddof=1)
                var_bmk = aligned.iloc[:, 1].var(ddof=1)
                beta = cov / var_bmk
            else:
                logger.warning(
                    "[%s] Insufficient aligned observations (%d < 30) or zero benchmark variance for Beta; returning NaN.",
                    ticker,
                    len(aligned),
                )
                beta = np.nan

        return {
            "ticker": ticker,
            "cagr_pct": round(cagr * 100.0, 4) if pd.notna(cagr) else None,
            "annualized_volatility_pct": round(ann_vol * 100.0, 4) if pd.notna(ann_vol) else None,
            "sharpe_ratio": round(float(sharpe), 4) if pd.notna(sharpe) else None,
            "max_drawdown_pct": round(float(max_drawdown) * 100.0, 4) if pd.notna(max_drawdown) else None,
            "var_95_pct": round(float(var_95) * 100.0, 4) if pd.notna(var_95) else None,
            "beta_nifty": round(float(beta), 4) if pd.notna(beta) else None,
            "last_close": round(float(last_close), 2) if pd.notna(last_close) else None,
            "52w_high": round(float(w52_high), 2) if pd.notna(w52_high) else None,
            "52w_low": round(float(w52_low), 2) if pd.notna(w52_low) else None,
            "trading_return_intervals": int(trading_return_intervals),
            "calendar_duration_years": round(float(calendar_duration_years), 4),
        }

    def compute_correlation_matrix(
        self,
        engineered_dict: Dict[str, pd.DataFrame],
    ) -> Tuple[List[str], np.ndarray]:
        """Compute joint inner-join Pearson correlation matrix across all instruments."""
        return_series = {}
        for ticker, df in engineered_dict.items():
            return_series[ticker] = df.set_index("Date")["daily_return"].dropna()

        joint_df = pd.DataFrame(return_series).dropna()
        tickers = list(joint_df.columns)
        corr_matrix = joint_df.corr(method="pearson").values
        return tickers, corr_matrix

    def run_all(
        self,
        instruments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute feature engineering across all instruments and compile summary tables."""
        tickers = instruments or DEFAULT_INSTRUMENTS
        engineered_dict: Dict[str, pd.DataFrame] = {}

        logger.info("Starting feature engineering for %d instruments: %s", len(tickers), tickers)

        # 1. Engineer individual instrument datasets
        for ticker in tickers:
            cleaned_path = self.processed_dir / f"{ticker}_cleaned.csv"
            if not cleaned_path.exists():
                raise FileNotFoundError(f"Cleaned dataset missing: {cleaned_path}")

            cleaned_df = pd.read_csv(cleaned_path)
            eng_df = self.engineer_instrument(cleaned_df, ticker)

            out_path = self.processed_dir / f"{ticker}_engineered.csv"
            eng_df.to_csv(out_path, index=False)
            logger.info("Saved single-source-of-truth dataset: %s (%d rows)", out_path, len(eng_df))
            engineered_dict[ticker] = eng_df

        # 2. Extract benchmark return series for Beta calculation
        if self.benchmark_ticker not in engineered_dict:
            raise ValueError(f"Benchmark ticker {self.benchmark_ticker} not found in engineered datasets.")
        benchmark_returns = (
            engineered_dict[self.benchmark_ticker].set_index("Date")["daily_return"].dropna()
        )

        # 3. Master Summary Metrics Table
        summary_rows = []
        for ticker in tickers:
            row = self.compute_summary_row(engineered_dict[ticker], ticker, benchmark_returns)
            summary_rows.append(row)

        summary_df = pd.DataFrame(summary_rows)
        summary_csv_path = self.processed_dir / "market_summary_metrics.csv"
        summary_df.to_csv(summary_csv_path, index=False)
        logger.info("Saved master market summary metrics: %s", summary_csv_path)

        # 4. Joint Correlation Matrix
        corr_tickers, corr_matrix = self.compute_correlation_matrix(engineered_dict)

        return {
            "engineered_dict": engineered_dict,
            "summary_df": summary_df,
            "correlation_tickers": corr_tickers,
            "correlation_matrix": corr_matrix,
        }


if __name__ == "__main__":
    from src.logger import setup_logging
    setup_logging()
    engineer = FeatureEngineer()
    res = engineer.run_all()
    print("\nFeature Engineering completed successfully.")
    print("Market Summary Metrics Table:")
    print(res["summary_df"].to_string(index=False))
