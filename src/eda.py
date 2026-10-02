"""Exploratory Data Analysis (EDA) Module for Stock Market Data Analyzer.

Generates 5 publication-grade 300 DPI visualizations and statistical digests
from cleaned historical equity datasets without mutating source cleaned files.
"""

import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for automated plotting
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import DEFAULT_INSTRUMENTS

# Publication Palette & Styling
COLOR_PALETTE = {
    "RELIANCE.NS": "#1f77b4",   # Deep Blue
    "TCS.NS": "#ff7f0e",        # Vibrant Orange
    "INFY.NS": "#2ca02c",       # Forest Green
    "SBIN.NS": "#d62728",       # Crimson Red
    "ICICIBANK.NS": "#9467bd",  # Purple
    "^NSEI": "#111827",         # Charcoal / Benchmark Black
}


class EDAAnalyzer:
    """Performs exploratory data analysis and exports high-resolution visual assets."""

    def __init__(
        self,
        processed_dir: str = "data/processed",
        output_dir: str = "outputs/eda",
    ) -> None:
        self.processed_dir = Path(processed_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", font="sans-serif")

    def load_cleaned_datasets(
        self,
        instruments: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Load cleaned datasets into memory for analysis without modifying disk files."""
        tickers = instruments or DEFAULT_INSTRUMENTS
        datasets: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            path = self.processed_dir / f"{ticker}_cleaned.csv"
            if not path.exists():
                raise FileNotFoundError(f"Cleaned dataset not found: {path}")
            df = pd.read_csv(path)
            df["Date"] = pd.to_datetime(df["Date"])
            datasets[ticker] = df
        return datasets

    def generate_summary_statistics(
        self,
        datasets: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Compute statistical summary on adjusted close and volume."""
        records = []
        for ticker, df in datasets.items():
            adj_close = df["adj_close"]
            returns = adj_close.pct_change().dropna()
            volume = df["Volume"]

            rec = {
                "Ticker": ticker,
                "Observations": len(df),
                "Mean Price": adj_close.mean(),
                "Std Price": adj_close.std(),
                "52W High": adj_close.tail(252).max() if len(adj_close) >= 252 else adj_close.max(),
                "52W Low": adj_close.tail(252).min() if len(adj_close) >= 252 else adj_close.min(),
                "Mean Daily Return (%)": returns.mean() * 100,
                "Return Std Dev (%)": returns.std() * 100,
                "Return Skewness": stats.skew(returns),
                "Return Kurtosis": stats.kurtosis(returns),
                "Avg Daily Volume": volume.mean(),
            }
            records.append(rec)
        return pd.DataFrame(records)

    def plot_01_historical_closing_trends(
        self,
        datasets: Dict[str, pd.DataFrame],
    ) -> Path:
        """Plot 5-year normalized closing trends (Base 100 from own first valid date)."""
        fig, ax = plt.subplots(figsize=(14, 7), dpi=300)

        for ticker, df in datasets.items():
            base_price = df["adj_close"].iloc[0]
            normalized = (df["adj_close"] / base_price) * 100
            color = COLOR_PALETTE.get(ticker, "#333333")
            linewidth = 2.4 if ticker == "^NSEI" else 1.8
            linestyle = "--" if ticker == "^NSEI" else "-"
            label = f"{ticker} (Benchmark)" if ticker == "^NSEI" else ticker

            ax.plot(
                df["Date"],
                normalized,
                label=label,
                color=color,
                linewidth=linewidth,
                linestyle=linestyle,
                alpha=0.9,
            )

        ax.axhline(100, color="#888888", linestyle=":", linewidth=1.2, label="Base 100 Baseline")
        ax.set_title(
            "Historical Closing Price Trajectories (Normalized Base 100: Sep 2021 – Sep 2026)",
            fontsize=15,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Date", fontsize=12, labelpad=10)
        ax.set_ylabel("Normalized Price (Base 100)", fontsize=12, labelpad=10)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.legend(loc="upper left", frameon=True, framealpha=0.9, fontsize=10)
        plt.tight_layout()

        out_file = self.output_dir / "01_historical_closing_trends.png"
        fig.savefig(out_file, dpi=300)
        plt.close(fig)
        return out_file

    def plot_02_trading_volume_distribution(
        self,
        datasets: Dict[str, pd.DataFrame],
    ) -> Path:
        """Plot trading volume boxplots across equities (excluding zero-volume days)."""
        fig, (ax_box, ax_bar) = plt.subplots(1, 2, figsize=(16, 7), dpi=300)

        # 1. Boxplot (in millions of shares, equities only)
        box_data = []
        labels = []
        equity_tickers = [t for t in datasets.keys() if t != "^NSEI"]

        for ticker in equity_tickers:
            vols = datasets[ticker]["Volume"]
            vols_clean = vols[vols > 0] / 1e6
            box_data.append(vols_clean)
            labels.append(ticker.replace(".NS", ""))

        bplot = ax_box.boxplot(
            box_data,
            patch_artist=True,
            tick_labels=labels,
            showfliers=False,  # Exclude extreme outliers for clear distribution comparison
            medianprops=dict(color="#111827", linewidth=1.5),
        )
        for patch, ticker in zip(bplot["boxes"], equity_tickers):
            patch.set_facecolor(COLOR_PALETTE.get(ticker, "#4a90e2"))
            patch.set_alpha(0.7)

        ax_box.set_title("Daily Trading Volume Distribution (Equity Shares)", fontsize=13, fontweight="bold")
        ax_box.set_ylabel("Volume (Million Shares)", fontsize=11)
        ax_box.set_xlabel("Equity Instrument", fontsize=11)

        # 2. Average Daily Turnover proxy / Mean volume bar chart
        mean_vols = [datasets[t]["Volume"].mean() / 1e6 for t in equity_tickers]
        colors = [COLOR_PALETTE.get(t, "#4a90e2") for t in equity_tickers]
        bars = ax_bar.bar(labels, mean_vols, color=colors, alpha=0.85, edgecolor="#333333", linewidth=0.8)
        for bar in bars:
            h = bar.get_height()
            ax_bar.annotate(
                f"{h:.1f}M",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )
        ax_bar.set_title("Average Daily Volume Comparison", fontsize=13, fontweight="bold")
        ax_bar.set_ylabel("Mean Daily Volume (Million Shares)", fontsize=11)
        ax_bar.set_xlabel("Equity Instrument", fontsize=11)

        fig.suptitle("Liquidity Profile and Trading Volume Analysis (2021–2026)", fontsize=15, fontweight="bold", y=1.02)
        plt.tight_layout()

        out_file = self.output_dir / "02_trading_volume_distribution.png"
        fig.savefig(out_file, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def plot_03_daily_returns_distribution(
        self,
        datasets: Dict[str, pd.DataFrame],
    ) -> Path:
        """Plot returns distribution histograms with normal overlay and KDE across 6 instruments."""
        fig, axes = plt.subplots(2, 3, figsize=(16, 10), dpi=300)
        axes = axes.flatten()

        for idx, (ticker, df) in enumerate(datasets.items()):
            ax = axes[idx]
            returns = df["adj_close"].pct_change().dropna() * 100  # in percent

            mu, std = returns.mean(), returns.std()
            skew, kurt = stats.skew(returns), stats.kurtosis(returns)

            # Histogram
            sns.histplot(
                returns,
                bins=50,
                kde=True,
                stat="density",
                ax=ax,
                color=COLOR_PALETTE.get(ticker, "#333333"),
                alpha=0.45,
                line_kws={"linewidth": 1.5, "label": "KDE Fit"},
            )

            # Normal Distribution PDF overlay
            x_grid = np.linspace(returns.min(), returns.max(), 300)
            norm_pdf = stats.norm.pdf(x_grid, mu, std)
            ax.plot(x_grid, norm_pdf, "r--", linewidth=1.8, label=f"Normal Fit\n(μ={mu:.2f}%, σ={std:.2f}%)")

            ax.set_title(
                f"{ticker}\nSkew: {skew:.2f} | Excess Kurt: {kurt:.2f}",
                fontsize=11,
                fontweight="bold",
            )
            ax.set_xlabel("Daily Return (%)", fontsize=10)
            ax.set_ylabel("Density", fontsize=10)
            ax.legend(fontsize=8, loc="upper right")

        fig.suptitle(
            "Empirical Daily Return Distributions vs. Gaussian Fit (Fat-Tail Analysis)",
            fontsize=15,
            fontweight="bold",
            y=1.01,
        )
        plt.tight_layout()

        out_file = self.output_dir / "03_daily_returns_distribution.png"
        fig.savefig(out_file, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return out_file

    def plot_04_cross_asset_correlation_matrix(
        self,
        datasets: Dict[str, pd.DataFrame],
    ) -> Path:
        """Plot complete-case cross-asset daily return correlation matrix heatmap."""
        # Align daily percentage returns on common dates (complete case)
        series_dict = {}
        for ticker, df in datasets.items():
            ret = df.set_index("Date")["adj_close"].pct_change().dropna()
            series_dict[ticker] = ret

        returns_df = pd.DataFrame(series_dict).dropna()
        corr_matrix = returns_df.corr(method="pearson")

        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
        cmap = sns.diverging_palette(240, 10, as_cmap=True)

        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".3f",
            cmap=cmap,
            vmin=0.0,
            vmax=1.0,
            square=True,
            linewidths=1.0,
            cbar_kws={"shrink": 0.8, "label": "Pearson Correlation Coefficient"},
            ax=ax,
            annot_kws={"size": 11, "weight": "bold"},
        )

        ax.set_title(
            f"Cross-Asset Daily Return Correlation Matrix\n(Complete-Case Joint Sample, N={len(returns_df)})",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        plt.xticks(rotation=45, ha="right", fontsize=10, fontweight="bold")
        plt.yticks(rotation=0, fontsize=10, fontweight="bold")
        plt.tight_layout()

        out_file = self.output_dir / "04_cross_asset_correlation_matrix.png"
        fig.savefig(out_file, dpi=300)
        plt.close(fig)
        return out_file

    def plot_05_rolling_30d_volatility_comparison(
        self,
        datasets: Dict[str, pd.DataFrame],
    ) -> Path:
        """Plot rolling 30-day annualized volatility comparison across all instruments."""
        fig, ax = plt.subplots(figsize=(14, 7), dpi=300)

        for ticker, df in datasets.items():
            returns = df["adj_close"].pct_change()
            # 30-day rolling standard deviation with ddof=1, annualized via sqrt(252)
            rolling_vol = returns.rolling(window=30, min_periods=30).std(ddof=1) * np.sqrt(252) * 100

            color = COLOR_PALETTE.get(ticker, "#333333")
            linewidth = 2.4 if ticker == "^NSEI" else 1.6
            linestyle = "--" if ticker == "^NSEI" else "-"
            label = f"{ticker} (Benchmark)" if ticker == "^NSEI" else ticker

            ax.plot(
                df["Date"],
                rolling_vol,
                label=label,
                color=color,
                linewidth=linewidth,
                linestyle=linestyle,
                alpha=0.85,
            )

        ax.set_title(
            "Rolling 30-Day Annualized Volatility (σ × √252, ddof=1)",
            fontsize=15,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Date", fontsize=12, labelpad=10)
        ax.set_ylabel("Annualized Volatility (%)", fontsize=12, labelpad=10)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.legend(loc="upper right", frameon=True, framealpha=0.9, fontsize=10)
        plt.tight_layout()

        out_file = self.output_dir / "05_rolling_30d_volatility_comparison.png"
        fig.savefig(out_file, dpi=300)
        plt.close(fig)
        return out_file

    def run_all(self) -> Dict[str, Path]:
        """Execute complete EDA analysis suite and export all 5 charts."""
        datasets = self.load_cleaned_datasets()
        logger.info("Loaded %d cleaned datasets for EDA.", len(datasets))

        summary_df = self.generate_summary_statistics(datasets)
        summary_path = self.output_dir / "eda_statistical_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        logger.info("Saved EDA statistical summary to %s", summary_path)

        plots = {
            "01_historical_closing_trends": self.plot_01_historical_closing_trends(datasets),
            "02_trading_volume_distribution": self.plot_02_trading_volume_distribution(datasets),
            "03_daily_returns_distribution": self.plot_03_daily_returns_distribution(datasets),
            "04_cross_asset_correlation_matrix": self.plot_04_cross_asset_correlation_matrix(datasets),
            "05_rolling_30d_volatility_comparison": self.plot_05_rolling_30d_volatility_comparison(datasets),
        }
        for name, p in plots.items():
            logger.info("Generated EDA visualization: %s", p)
        return plots


if __name__ == "__main__":
    from src.logger import setup_logging
    setup_logging()
    analyzer = EDAAnalyzer()
    analyzer.run_all()
    print("EDA execution successfully completed. 5 plots generated in outputs/eda/.")
