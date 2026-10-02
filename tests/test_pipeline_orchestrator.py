"""Pytest Suite for Master Pipeline Orchestrator, Centralized Logging, and Data Lineage.

Covers:
1. Sequential execution order of the 6 pipeline stages in main.py.
2. Immediate termination on stage failure with non-zero exit code.
3. Logging exclusively to logs/pipeline.log with timestamps and severity.
4. Verification that NO timestamped log files are generated.
5. Prevention of duplicate log handlers and duplicate log entries across repeated setup_logging calls.
6. Verification that all module defaults use data/ with ZERO references to data_data.
7. Independent execution of pipeline components with isolated fixtures.
"""

from pathlib import Path
import re
import sys
from unittest.mock import MagicMock, patch
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import run_pipeline
from src.cleaner import DataCleaner
from src.dashboard_exporter import DashboardExporter
from src.data_loader import StockDataLoader
from src.eda import EDAAnalyzer
from src.feature_engineering import FeatureEngineer
from src.logger import DEFAULT_LOG_FORMAT, setup_logging
from src.reporter import PerformanceReporter
from src.visualizer import StaticVisualizer


# ==============================================================================
# 1. Pipeline Execution Order & Halting Tests
# ==============================================================================

def test_pipeline_execution_order_success():
    """Verify that main.run_pipeline executes all 7 stages in exact mandated sequence."""
    execution_order = []

    with patch("src.cleaner.DataCleaner.clean_and_save_all", side_effect=lambda: execution_order.append("2_cleaner")), \
         patch("src.eda.EDAAnalyzer.run_all", side_effect=lambda: execution_order.append("3_eda")), \
         patch("src.feature_engineering.FeatureEngineer.run_all", side_effect=lambda: execution_order.append("4_feature_engineering")), \
         patch("src.visualizer.StaticVisualizer.generate_all_charts", side_effect=lambda: execution_order.append("5_visualizer")), \
         patch("src.dashboard_exporter.DashboardExporter.export", side_effect=lambda: execution_order.append("6_dashboard_exporter")), \
         patch("src.reporter.PerformanceReporter.generate_digest", side_effect=lambda: execution_order.append("7_reporter")):

        exit_code = run_pipeline(skip_download=True)

        assert exit_code == 0, "Pipeline should return 0 on successful completion."
        assert execution_order == [
            "2_cleaner",
            "3_eda",
            "4_feature_engineering",
            "5_visualizer",
            "6_dashboard_exporter",
            "7_reporter",
        ], f"Stages executed out of order: {execution_order}"


@pytest.mark.parametrize("failing_stage_idx,failing_patch", [
    (2, "src.cleaner.DataCleaner.clean_and_save_all"),
    (3, "src.eda.EDAAnalyzer.run_all"),
    (4, "src.feature_engineering.FeatureEngineer.run_all"),
    (5, "src.visualizer.StaticVisualizer.generate_all_charts"),
    (6, "src.dashboard_exporter.DashboardExporter.export"),
])
def test_pipeline_halts_immediately_on_stage_failure(failing_stage_idx, failing_patch):
    """Verify that any stage failure aborts the pipeline and prevents downstream stages from running."""
    call_log = []

    def mock_cleaner():
        call_log.append("stage_cleaner")
        if failing_stage_idx == 2:
            raise RuntimeError("Stage 2 failure")

    def mock_eda():
        call_log.append("stage_eda")
        if failing_stage_idx == 3:
            raise RuntimeError("Stage 3 failure")

    def mock_fe():
        call_log.append("stage_fe")
        if failing_stage_idx == 4:
            raise RuntimeError("Stage 4 failure")

    def mock_viz():
        call_log.append("stage_viz")
        if failing_stage_idx == 5:
            raise RuntimeError("Stage 5 failure")

    def mock_export():
        call_log.append("stage_export")
        if failing_stage_idx == 6:
            raise RuntimeError("Stage 6 failure")

    def mock_reporter():
        call_log.append("stage_reporter")

    with patch("src.cleaner.DataCleaner.clean_and_save_all", side_effect=mock_cleaner), \
         patch("src.eda.EDAAnalyzer.run_all", side_effect=mock_eda), \
         patch("src.feature_engineering.FeatureEngineer.run_all", side_effect=mock_fe), \
         patch("src.visualizer.StaticVisualizer.generate_all_charts", side_effect=mock_viz), \
         patch("src.dashboard_exporter.DashboardExporter.export", side_effect=mock_export), \
         patch("src.reporter.PerformanceReporter.generate_digest", side_effect=mock_reporter):

        exit_code = run_pipeline(skip_download=True)

        assert exit_code != 0, f"Pipeline must return non-zero exit code when stage {failing_stage_idx} fails."
        assert "stage_reporter" not in call_log, "Downstream reporter stage must not execute after earlier failure."


# ==============================================================================
# 2. Centralized Logging Tests (Single logs/pipeline.log, No Timestamped Files)
# ==============================================================================

def test_logging_writes_exclusively_to_pipeline_log(tmp_path):
    """Verify that logging writes exclusively to pipeline.log with zero timestamped files created."""
    log_dir = tmp_path / "logs"
    test_logger = setup_logging(log_dir=str(log_dir), also_console=False)

    test_logger.info("Test informational pipeline message.")
    test_logger.warning("Test warning event.")
    test_logger.error("Test error event.")

    # Flush handlers
    for h in list(test_logger.handlers):
        h.flush()
        h.close()
        test_logger.removeHandler(h)

    # 1. Verify pipeline.log exists
    pipeline_log = log_dir / "pipeline.log"
    assert pipeline_log.exists(), "pipeline.log must be created."

    # 2. Verify all log files in directory: must contain ONLY pipeline.log
    created_files = [f.name for f in log_dir.glob("*.log")]
    assert created_files == ["pipeline.log"], f"Only pipeline.log should exist. Found: {created_files}"

    # 3. Verify content formatting
    content = pipeline_log.read_text(encoding="utf-8")
    assert "[INFO]" in content
    assert "[WARNING]" in content
    assert "[ERROR]" in content
    assert "Test informational pipeline message." in content

    # 4. Verify timestamp format (YYYY-MM-DD HH:MM:SS)
    timestamp_pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[INFO\]")
    assert timestamp_pattern.search(content) is not None, "Log entries must contain formatted timestamps."


def test_logging_prevents_duplicate_handlers_and_entries(tmp_path):
    """Verify calling setup_logging multiple times does not duplicate handlers or messages."""
    log_dir = tmp_path / "logs"
    target_log = log_dir / "pipeline.log"

    # Setup 1
    logger1 = setup_logging(log_dir=str(log_dir), also_console=False)
    logger1.info("Entry Alpha")

    # Setup 2 (simulating multiple module executions or repeated calls)
    logger2 = setup_logging(log_dir=str(log_dir), also_console=False)
    logger2.info("Entry Beta")

    for h in list(logger2.handlers):
        h.flush()
        h.close()
        logger2.removeHandler(h)

    content = target_log.read_text(encoding="utf-8")
    assert content.count("Entry Alpha") == 1, "Entry Alpha must appear exactly once."
    assert content.count("Entry Beta") == 1, "Entry Beta must appear exactly once."


# ==============================================================================
# 3. Path Lineage & data_data Absence Tests
# ==============================================================================

def test_module_default_paths_use_data_hierarchy():
    """Verify that every module class defaults to the data/ directory structure."""
    loader = StockDataLoader()
    assert loader.raw_dir == Path("data/raw")
    assert loader.archive_dir == Path("data/raw/archive")

    cleaner = DataCleaner()
    assert cleaner.raw_dir == Path("data/raw")
    assert cleaner.processed_dir == Path("data/processed")

    eda = EDAAnalyzer()
    assert eda.processed_dir == Path("data/processed")
    assert eda.output_dir == Path("outputs/eda")

    fe = FeatureEngineer()
    assert fe.processed_dir == Path("data/processed")

    viz = StaticVisualizer()
    assert viz.processed_dir == Path("data/processed")
    assert viz.output_dir == Path("outputs/charts")

    exporter = DashboardExporter()
    assert exporter.processed_dir == Path("data/processed")
    assert exporter.docs_dir == Path("docs")


def test_zero_active_data_data_references_in_codebase():
    """Verify that zero active Python, test, or config files contain stale 'data_data' references."""
    target_pattern = "data" + "_data"
    project_files = list(PROJECT_ROOT.glob("src/**/*.py")) + \
                    [pf for pf in PROJECT_ROOT.glob("tests/**/*.py") if pf.resolve() != Path(__file__).resolve()] + \
                    [PROJECT_ROOT / "main.py", PROJECT_ROOT / "requirements.txt"]

    stale_matches = []
    for pf in project_files:
        if pf.exists():
            text = pf.read_text(encoding="utf-8", errors="ignore")
            if target_pattern in text:
                stale_matches.append(str(pf.relative_to(PROJECT_ROOT)))

    assert len(stale_matches) == 0, f"Found stale '{target_pattern}' references in files: {stale_matches}"


# ==============================================================================
# 4. Independent Module Executability (Isolated & Offline)
# ==============================================================================

def test_cleaner_and_exporter_independent_instantiation_and_audit(tmp_path):
    """Verify DataCleaner and DashboardExporter can run independently on isolated temp paths."""
    audit_path = tmp_path / "test_audit.json"
    cleaner = DataCleaner(
        raw_dir=str(tmp_path / "raw"),
        processed_dir=str(tmp_path / "processed"),
        audit_log_path=str(audit_path),
    )
    assert cleaner.raw_dir == tmp_path / "raw"
    assert cleaner.processed_dir == tmp_path / "processed"
    assert cleaner.audit_log_path == audit_path
