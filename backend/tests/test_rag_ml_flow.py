import os
import importlib
import sys
from unittest.mock import MagicMock, patch

# Set required env vars before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("VITE_API_BASE_URL", "http://localhost:8000")


def _reload_ml_flow(fake_mlflow: MagicMock):
    """Reload the ml_flow module with a mocked mlflow."""
    with patch.dict(sys.modules, {"mlflow": fake_mlflow}):
        ml_flow = importlib.import_module("app.modules.rag.ml_flow")
        return importlib.reload(ml_flow)


def _mock_run():
    """Return a mock context-manager run object."""
    mock_run = MagicMock()
    mock_run.__enter__.return_value = mock_run
    mock_run.__exit__.return_value = None
    return mock_run


def test_log_query_records_rag_metrics():
    fake_mlflow = MagicMock()
    ml_flow = _reload_ml_flow(fake_mlflow)
    mock_run = _mock_run()

    with (
        patch.object(ml_flow.settings, "MLFLOW_TRACKING_URI", ""),
        patch.object(fake_mlflow, "start_run", return_value=mock_run),
        patch.object(fake_mlflow, "log_param") as mock_log_param,
        patch.object(fake_mlflow, "log_metric") as mock_log_metric,
        patch.object(fake_mlflow, "log_text") as mock_log_text,
    ):
        ml_flow.log_query(
            question="What does the EU AI Act require?",
            answer="Maintain technical documentation.",
            sources=["eu_ai_act.pdf", "iso_42001.pdf"],
            latency_ms=125.5,
        )

    mock_log_param.assert_called_once_with(
        "question",
        "What does the EU AI Act require?",
    )
    mock_log_metric.assert_any_call("answer_length", 33)
    mock_log_metric.assert_any_call("source_count", 2)
    mock_log_metric.assert_any_call("response_latency_ms", 125.5)
    mock_log_text.assert_called_once_with("Maintain technical documentation.", "answer.txt")


def test_log_query_sets_tracking_uri_when_configured():
    """When MLFLOW_TRACKING_URI is set, it should be applied to mlflow."""
    fake_mlflow = MagicMock()
    ml_flow = _reload_ml_flow(fake_mlflow)
    mock_run = _mock_run()

    with (
        patch.object(ml_flow.settings, "MLFLOW_TRACKING_URI", "http://mlflow.example.com"),
        patch.object(fake_mlflow, "set_tracking_uri") as mock_set_uri,
        patch.object(fake_mlflow, "start_run", return_value=mock_run),
        patch.object(fake_mlflow, "log_param"),
        patch.object(fake_mlflow, "log_metric"),
        patch.object(fake_mlflow, "log_text"),
    ):
        ml_flow.log_query(
            question="Test question?",
            answer="Test answer.",
            sources=[],
            latency_ms=0.0,
        )
    mock_set_uri.assert_called_once_with("http://mlflow.example.com")


def test_log_query_truncates_long_question_to_500_chars():
    """Long questions should be truncated to 500 chars to stay within MLflow limits."""
    fake_mlflow = MagicMock()
    ml_flow = _reload_ml_flow(fake_mlflow)
    mock_run = _mock_run()

    with (
        patch.object(ml_flow.settings, "MLFLOW_TRACKING_URI", ""),
        patch.object(fake_mlflow, "start_run", return_value=mock_run),
        patch.object(fake_mlflow, "log_param") as mock_log_param,
        patch.object(fake_mlflow, "log_metric"),
        patch.object(fake_mlflow, "log_text"),
    ):
        long_question = "A" * 1000
        ml_flow.log_query(question=long_question, answer="Short", sources=[], latency_ms=0.0)
    # Truncated to 500 chars
    assert len(mock_log_param.call_args_list[0][0][1]) == 500


def test_log_query_handles_empty_sources():
    """log_query should handle empty sources list without crashing."""
    fake_mlflow = MagicMock()
    ml_flow = _reload_ml_flow(fake_mlflow)
    mock_run = _mock_run()

    with (
        patch.object(ml_flow.settings, "MLFLOW_TRACKING_URI", ""),
        patch.object(fake_mlflow, "start_run", return_value=mock_run),
        patch.object(fake_mlflow, "log_param"),
        patch.object(fake_mlflow, "log_metric") as mock_log_metric,
        patch.object(fake_mlflow, "log_text"),
    ):
        ml_flow.log_query(question="Q?", answer="A.", sources=[], latency_ms=0.0)
    mock_log_metric.assert_any_call("source_count", 0)


def test_log_query_swallows_mlflow_exceptions():
    """MLflow failures should be caught and logged as warnings, not propagated."""
    fake_mlflow = MagicMock()
    ml_flow = _reload_ml_flow(fake_mlflow)

    with (
        patch.object(ml_flow.settings, "MLFLOW_TRACKING_URI", ""),
        patch.object(
            fake_mlflow, "start_run",
            side_effect=RuntimeError("MLflow connection failed"),
        ),
    ):
        # Should not raise — exception is swallowed
        ml_flow.log_query(question="Q?", answer="A.", sources=[], latency_ms=0.0)
