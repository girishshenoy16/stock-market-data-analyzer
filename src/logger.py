"""Centralized Logging Configuration Module for Stock Market Data Analyzer.

Provides unified logging setup for the master orchestrator (main.py)
and standalone module executions, saving exclusively to console and
the single cumulative file sink: logs/pipeline.log.
"""

from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Optional, Union

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: str = "logs",
    log_file: Optional[Union[str, Path]] = None,
    level: int = logging.INFO,
    also_console: bool = True,
) -> logging.Logger:
    """Configures centralized logging for the pipeline and individual modules.

    Guarantees:
    - Exclusively writes file logs to logs/pipeline.log (zero timestamped log files created).
    - Writes formatted entries with timestamp, severity level, module name, and message.
    - Console output attached via StreamHandler.
    - Automatically creates log_dir / parent directories if they do not exist.
    - Clears existing handlers to prevent duplicate log entries or duplicate handlers.

    Args:
        log_dir: Directory where pipeline.log is stored (default 'logs').
        log_file: Optional explicit file path overriding default log_dir/pipeline.log.
        level: Logging level (default INFO).
        also_console: Whether to attach console StreamHandler.

    Returns:
        Configured root logger instance.
    """
    if log_file is not None:
        target_file = Path(log_file)
        target_dir = target_file.parent
    else:
        target_dir = Path(log_dir)
        target_file = target_dir / "pipeline.log"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        sys.stderr.write(f"CRITICAL: Failed to create log directory '{target_dir}': {e}\n")
        raise

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to prevent duplicate log entries
    if root_logger.hasHandlers():
        for h in list(root_logger.handlers):
            try:
                h.flush()
                h.close()
            except Exception:
                pass
        root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    handlers = []

    # 1. Console StreamHandler
    if also_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # 2. Single Cumulative FileHandler (logs/pipeline.log)
    try:
        file_handler = logging.FileHandler(target_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    except Exception as e:
        sys.stderr.write(f"CRITICAL: Could not attach pipeline file logger '{target_file}': {e}\n")
        raise

    for h in handlers:
        root_logger.addHandler(h)

    # Silence noisy third-party libraries to prevent log-flooding during verbose/debug mode
    for noisy_logger in ["matplotlib", "PIL", "urllib3", "fontTools"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    return root_logger


if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Centralized logging system initialized — writing to logs/pipeline.log.")
    logger.warning("Sample warning recorded in single log file.")
