"""Regression tests for guard_config path resolution.

These tests prevent regressions in path variables that previously broke —
DATA_DIR, MODELS_DIR, BACKEND_ROOT, and get_trained_model_path().
"""

from pathlib import Path
from unittest.mock import patch

import importlib.util, sys

spec = importlib.util.spec_from_file_location(
    "guard_config",
    __import__("pathlib").Path(__file__).parent.parent
    / "app/modules/guard/guard_config.py",
)
guard_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard_config)


_GUARD_CONFIG_FILE = Path(guard_config.__file__).resolve()
_EXPECTED_BACKEND_ROOT = _GUARD_CONFIG_FILE.parent.parent.parent.parent


class TestPathResolution:
    def test_backend_root_resolves_to_backend(self):
        assert guard_config.BACKEND_ROOT.resolve() == _EXPECTED_BACKEND_ROOT

    def test_data_dir_resolves_under_backend(self):
        assert guard_config.DATA_DIR.resolve() == _EXPECTED_BACKEND_ROOT / "data"

    def test_models_dir_resolves_under_guard(self):
        expected = _GUARD_CONFIG_FILE.parent / "models"
        assert guard_config.MODELS_DIR.resolve() == expected.resolve()

    def test_backend_root_name_is_backend(self):
        assert guard_config.BACKEND_ROOT.name == "backend"

    def test_data_dir_name_is_data(self):
        assert guard_config.DATA_DIR.name == "data"

    def test_models_dir_name_is_models(self):
        assert guard_config.MODELS_DIR.name == "models"


class TestGetTrainedModelPath:
    def test_returns_default_when_no_fine_tuned_model(self):
        with patch("os.path.exists", return_value=False):
            result = guard_config.get_trained_model_path()
        assert result == guard_config.CLASSIFIER_MODEL_PATH

    def test_returns_string(self):
        with patch("os.path.exists", return_value=False):
            result = guard_config.get_trained_model_path()
        assert isinstance(result, str)

    def test_returns_env_path_when_it_exists(self):
        with patch("os.path.exists", return_value=True):
            result = guard_config.get_trained_model_path()
        assert result == guard_config.CLASSIFIER_MODEL_PATH
