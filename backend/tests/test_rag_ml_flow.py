import importlib
import sys
from unittest.mock import MagicMock, patch


def test_log_query_records_rag_metrics():
    fake_mlflow = MagicMock()
    with patch.dict(sys.modules, {"mlflow": fake_mlflow}):
        ml_flow = importlib.import_module("app.modules.rag.ml_flow")
        ml_flow = importlib.reload(ml_flow)

    mock_run = MagicMock()
    mock_run.__enter__.return_value = mock_run
    mock_run.__exit__.return_value = None

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
