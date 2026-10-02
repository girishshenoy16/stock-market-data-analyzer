"""Master Pipeline Orchestrator for Stock Market Data Analyzer.

Sequentially executes the core analytics pipeline in strict sequential order:
1. src.data_loader (Data Ingestion & Archival)
2. src.cleaner (Data Cleaning & Validation)
3. src.eda (Exploratory Data Analysis)
4. src.feature_engineering (Feature Engineering & Summary Metrics)
5. src.visualizer (Static Analytical Visualizations)
6. src.dashboard_exporter (Web Dashboard Data Bundle Export)
7. src.reporter (Performance Reporting & Digest Generation)

Guarantees immediate halt on failure, non-zero exit codes, execution timing,
and centralized logging to console and logs/ directory.
"""

import argparse
from datetime import datetime
import logging
import sys
import time
from typing import Any, Callable, Dict, List, Tuple

from src.cleaner import DataCleaner
from src.dashboard_exporter import DashboardExporter
from src.data_loader import StockDataLoader
from src.eda import EDAAnalyzer
from src.feature_engineering import FeatureEngineer
from src.logger import setup_logging
from src.reporter import PerformanceReporter
from src.visualizer import StaticVisualizer

logger = logging.getLogger("orchestrator")


def run_pipeline(skip_download: bool = False) -> int:
    """Executes the 7 pipeline stages sequentially.

    Args:
        skip_download: If True, uses existing cached raw data instead of downloading
                       from Yahoo Finance (enables offline validation).

    Returns:
        Exit code: 0 on success, non-zero (1) on stage failure.
    """
    pipeline_start = time.perf_counter()
    logger.info("================================================================================")
    logger.info("STOCK MARKET DATA ANALYZER — MASTER PIPELINE EXECUTION STARTED")
    logger.info("Timestamp: %s | Python: %s", datetime.now().isoformat(), sys.version.split()[0])
    logger.info("================================================================================")

    # Define the 7 stages in exact mandated sequence
    stages: List[Tuple[str, str, Callable[[], Any]]] = [
        (
            "1. Data Ingestion & Snapshot Archival",
            "src.data_loader",
            lambda: (
                logger.info("Using cached raw data in data/raw/ (--skip-download active).")
                if skip_download
                else StockDataLoader().download_all()
            ),
        ),
        (
            "2. Data Cleaning & Validation",
            "src.cleaner",
            lambda: DataCleaner().clean_and_save_all(),
        ),
        (
            "3. Exploratory Data Analysis (EDA)",
            "src.eda",
            lambda: EDAAnalyzer().run_all(),
        ),
        (
            "4. Feature Engineering & Financial Analytics",
            "src.feature_engineering",
            lambda: FeatureEngineer().run_all(),
        ),
        (
            "5. Static Analytical Visualizations",
            "src.visualizer",
            lambda: StaticVisualizer().generate_all_charts(),
        ),
        (
            "6. Web Dashboard Data Bundle Export",
            "src.dashboard_exporter",
            lambda: DashboardExporter().export(),
        ),
        (
            "7. Performance Reporting & Digest Generation",
            "src.reporter",
            lambda: PerformanceReporter().generate_digest(),
        ),
    ]

    stage_records: List[Dict[str, Any]] = []

    for idx, (stage_name, module_name, stage_fn) in enumerate(stages, start=1):
        stage_start = time.perf_counter()
        logger.info(">>> [Stage %d/%d] Starting: %s (%s)", idx, len(stages), stage_name, module_name)

        try:
            stage_fn()
            duration = time.perf_counter() - stage_start
            logger.info("<<< [Stage %d/%d] COMPLETED: %s (Duration: %.2f seconds)", idx, len(stages), stage_name, duration)
            stage_records.append({
                "stage_idx": idx,
                "stage_name": stage_name,
                "module": module_name,
                "status": "SUCCESS",
                "duration_seconds": round(duration, 2),
            })
        except Exception as e:
            duration = time.perf_counter() - stage_start
            logger.error("!!! [Stage %d/%d] FAILED: %s (Duration: %.2f seconds)", idx, len(stages), stage_name, duration)
            logger.exception("Exception traceback for stage '%s': %s", stage_name, e)
            stage_records.append({
                "stage_idx": idx,
                "stage_name": stage_name,
                "module": module_name,
                "status": "FAILED",
                "duration_seconds": round(duration, 2),
                "error": str(e),
            })

            # Report clearly and halt immediately
            total_elapsed = time.perf_counter() - pipeline_start
            sys.stderr.write(
                f"\n[FATAL ERROR] Pipeline terminated prematurely at Stage {idx}: '{stage_name}'\n"
                f"Module: {module_name}\n"
                f"Error: {e}\n"
                f"Subsequent stages will not be executed.\n"
                f"Total elapsed before failure: {total_elapsed:.2f}s\n"
            )
            return 1

    total_duration = time.perf_counter() - pipeline_start
    logger.info("================================================================================")
    logger.info("ALL PIPELINE STAGES COMPLETED SUCCESSFULLY")
    logger.info("Total Pipeline Duration: %.2f seconds", total_duration)
    logger.info("--------------------------------------------------------------------------------")
    logger.info("%-4s | %-45s | %-10s | %s", "Step", "Stage Name", "Status", "Duration")
    logger.info("--------------------------------------------------------------------------------")
    for r in stage_records:
        logger.info("%-4d | %-45s | %-10s | %.2fs", r["stage_idx"], r["stage_name"], r["status"], r["duration_seconds"])
    logger.info("================================================================================")

    print("\nPipeline execution summary:")
    for r in stage_records:
        print(f"  [{r['status']}] Stage {r['stage_idx']}: {r['stage_name']} ({r['duration_seconds']}s)")
    print(f"\nTotal Elapsed Time: {total_duration:.2f}s\n")

    return 0


def main() -> None:
    """CLI entry point for master pipeline orchestration."""
    parser = argparse.ArgumentParser(
        description="Master Pipeline Orchestrator for Stock Market Data Analyzer."
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading live market data and reuse cached raw data in data/raw/",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging to console and pipeline.log",
    )
    parser.add_argument(
        "--re-run",
        action="store_true",
        help="Execute full pipeline re-run across all stages",
    )
    args = parser.parse_args()

    # Initialize centralized logging exclusively to logs/pipeline.log
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)

    # Explicit --skip-download always takes precedence to guarantee offline execution
    # When --skip-download is omitted, download runs (preserving default and --re-run behavior)
    skip_download = args.skip_download
    exit_code = run_pipeline(skip_download=skip_download)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
