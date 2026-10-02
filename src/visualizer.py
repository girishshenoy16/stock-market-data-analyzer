"""Static Visualizer Module for Stock Market Data Analyzer.

Generates 18 publication-grade, 300 DPI analytical charts across all
6 instruments: trend indicators with moving average crossovers,
Bollinger Bands with Wilder's RSI, and underwater drawdown profiles.
"""

import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import DEFAULT_INSTRUMENTS

logger = logging.getLogger(__name__)


class StaticVisualizer:
    """Produces publication-ready financial charts from engineered stock datasets."""

    def __init__(
        self,
        processed_dir: str = "data/processed",
        output_dir: str = "outputs/charts",
    ) -> None:
        self.processed_dir = Path(processed_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", font="sans-serif")

    def load_engineered_data(self, ticker: str) -> pd.DataFrame:
        """Load single engineered dataset and parse dates."""
        path = self.processed_dir / f"{ticker}_engineered.csv"
        if not path.exists():
            raise FileNotFoundError(f"Engineered dataset missing: {path}")
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"])
        return df

    def plot_trend_indicators(self, df: pd.DataFrame, ticker: str) -> Path:
        """Plot price, moving averages, and crossover signals."""
        fig, ax = plt.subplots(figsize=(14, 7), dpi=300)

        # Base price line
        ax.plot(df["Date"], df["adj_close"], label="Effective Adj Close", color="#0f172a", linewidth=1.8, alpha=0.95)
        # Moving averages
        ax.plot(df["Date"], df["sma_20"], label="SMA 20", color="#3b82f6", linewidth=1.2, linestyle="-", alpha=0.85)
        ax.plot(df["Date"], df["sma_50"], label="SMA 50", color="#f59e0b", linewidth=1.3, linestyle="-", alpha=0.85)
        ax.plot(df["Date"], df["sma_200"], label="SMA 200", color="#dc2626", linewidth=1.6, linestyle="-", alpha=0.9)
        ax.plot(df["Date"], df["ema_20"], label="EMA 20", color="#10b981", linewidth=1.1, linestyle="--", alpha=0.8)

        # Crossover Markers
        golden_crosses = df[df["golden_cross_event"] == 1]
        death_crosses = df[df["death_cross_event"] == 1]

        if not golden_crosses.empty:
            ax.scatter(
                golden_crosses["Date"],
                golden_crosses["adj_close"],
                marker="^",
                color="#16a34a",
                s=120,
                label=f"Golden Cross (SMA50 > SMA200, N={len(golden_crosses)})",
                zorder=5,
                edgecolors="black",
                linewidth=0.8,
            )

        if not death_crosses.empty:
            ax.scatter(
                death_crosses["Date"],
                death_crosses["adj_close"],
                marker="v",
                color="#ef4444",
                s=120,
                label=f"Death Cross (SMA50 < SMA200, N={len(death_crosses)})",
                zorder=5,
                edgecolors="black",
                linewidth=0.8,
            )

        ax.set_title(
            f"{ticker} — Trend Indicators & Technical Moving Average Regimes",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Date", fontsize=11, labelpad=10)
        ax.set_ylabel("Price (₹ / Index Points)", fontsize=11, labelpad=10)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.legend(loc="upper left", frameon=True, framealpha=0.95, fontsize=9)
        plt.tight_layout()

        out_path = self.output_dir / f"{ticker}_trend_indicators.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        return out_path

    def plot_bollinger_rsi(self, df: pd.DataFrame, ticker: str) -> Path:
        """Plot 2-panel chart: Upper Bollinger Bands, Lower Wilder's RSI-14."""
        fig, (ax_bb, ax_rsi) = plt.subplots(
            2, 1, figsize=(14, 9), dpi=300, sharex=True, gridspec_kw={"height_ratios": [2.2, 1.0]}
        )

        # Upper Panel: Bollinger Bands
        ax_bb.plot(df["Date"], df["adj_close"], label="Effective Adj Close", color="#0f172a", linewidth=1.5)
        ax_bb.plot(df["Date"], df["bb_middle"], label="Middle Band (SMA 20)", color="#3b82f6", linewidth=1.2, linestyle="--")
        ax_bb.plot(df["Date"], df["bb_upper"], label="Upper Band (+2σ)", color="#8b5cf6", linewidth=1.0)
        ax_bb.plot(df["Date"], df["bb_lower"], label="Lower Band (-2σ)", color="#8b5cf6", linewidth=1.0)
        ax_bb.fill_between(df["Date"], df["bb_lower"], df["bb_upper"], color="#8b5cf6", alpha=0.12, label="Band Envelopment")

        ax_bb.set_title(f"{ticker} — Bollinger Bands (20, 2) & Wilder's RSI (14)", fontsize=14, fontweight="bold", pad=12)
        ax_bb.set_ylabel("Price (₹ / Points)", fontsize=11)
        ax_bb.legend(loc="upper left", frameon=True, framealpha=0.9, fontsize=9)

        # Lower Panel: Wilder's RSI-14
        ax_rsi.plot(df["Date"], df["rsi_14"], label="Wilder's RSI (14)", color="#d97706", linewidth=1.4)
        ax_rsi.axhline(70, color="#ef4444", linestyle=":", linewidth=1.2, label="Overbought (70)")
        ax_rsi.axhline(30, color="#10b981", linestyle=":", linewidth=1.2, label="Oversold (30)")
        ax_rsi.axhline(50, color="#6b7280", linestyle="-.", linewidth=0.8, alpha=0.7)
        ax_rsi.fill_between(df["Date"], 70, df["rsi_14"], where=(df["rsi_14"] >= 70), color="#ef4444", alpha=0.3)
        ax_rsi.fill_between(df["Date"], 30, df["rsi_14"], where=(df["rsi_14"] <= 30), color="#10b981", alpha=0.3)

        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel("RSI (0–100)", fontsize=11)
        ax_rsi.set_xlabel("Date", fontsize=11, labelpad=8)
        ax_rsi.xaxis.set_major_locator(mdates.YearLocator())
        ax_rsi.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax_rsi.legend(loc="upper left", frameon=True, framealpha=0.9, fontsize=9)

        plt.tight_layout()
        out_path = self.output_dir / f"{ticker}_bollinger_rsi.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        return out_path

    def plot_drawdown_underwater(self, df: pd.DataFrame, ticker: str) -> Path:
        """Plot peak-to-trough historical drawdown profile with underwater fill."""
        fig, ax = plt.subplots(figsize=(14, 6), dpi=300)

        dd_pct = df["drawdown"] * 100.0  # in percent
        ax.plot(df["Date"], dd_pct, color="#dc2626", linewidth=1.4, label="Drawdown Profile")
        ax.fill_between(df["Date"], dd_pct, 0, color="#dc2626", alpha=0.25, label="Underwater Area")

        # Reference lines
        ax.axhline(0, color="#111827", linewidth=1.0, linestyle="-")
        ax.axhline(-10, color="#6b7280", linewidth=0.8, linestyle=":", label="Threshold -10%")
        ax.axhline(-20, color="#f59e0b", linewidth=0.8, linestyle=":", label="Bear Market Threshold -20%")

        # Annotate Maximum Drawdown (MDD)
        mdd_val = dd_pct.min()
        mdd_idx = dd_pct.idxmin()
        mdd_date = df.loc[mdd_idx, "Date"]

        ax.scatter([mdd_date], [mdd_val], color="#7f1d1d", s=90, zorder=5)
        ax.annotate(
            f"Max Drawdown: {mdd_val:.2f}%\n({mdd_date.strftime('%Y-%m-%d')})",
            xy=(mdd_date, mdd_val),
            xytext=(15, -25),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="#7f1d1d", lw=1.2),
            fontsize=9,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", fc="#fee2e2", ec="#dc2626", lw=1),
        )

        ax.set_title(f"{ticker} — Peak-to-Trough Drawdown & Capital Preservation Profile", fontsize=14, fontweight="bold", pad=15)
        ax.set_xlabel("Date", fontsize=11, labelpad=10)
        ax.set_ylabel("Drawdown (%)", fontsize=11, labelpad=10)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.legend(loc="lower left", frameon=True, framealpha=0.9, fontsize=9)
        plt.tight_layout()

        out_path = self.output_dir / f"{ticker}_drawdown_underwater.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        return out_path

    def generate_all_charts(
        self,
        instruments: Optional[List[str]] = None,
    ) -> List[Path]:
        """Generate all 3 chart types for each instrument (18 charts total)."""
        tickers = instruments or DEFAULT_INSTRUMENTS
        generated: List[Path] = []

        logger.info("Generating static analytical figures for %d instruments: %s", len(tickers), tickers)

        for ticker in tickers:
            df = self.load_engineered_data(ticker)

            p1 = self.plot_trend_indicators(df, ticker)
            p2 = self.plot_bollinger_rsi(df, ticker)
            p3 = self.plot_drawdown_underwater(df, ticker)

            generated.extend([p1, p2, p3])
            logger.info("Saved 3 static figures for %s", ticker)

        logger.info("Successfully generated %d publication charts in %s", len(generated), self.output_dir)
        return generated


if __name__ == "__main__":
    from src.logger import setup_logging
    setup_logging()
    visualizer = StaticVisualizer()
    charts = visualizer.generate_all_charts()
    print(f"\nStatic Visualizer complete. Total charts generated: {len(charts)}")
