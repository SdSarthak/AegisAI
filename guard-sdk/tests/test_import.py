import aegisai_guard

def test_import():
    """Verify that the package can be imported and has a version string."""
    assert hasattr(aegisai_guard, "__version__")
    assert isinstance(aegisai_guard.__version__, str)
    assert aegisai_guard.__version__ == "0.1.0"

def test_api_availability():
    """Verify that the main API classes are available."""
    from aegisai_guard import LLMGuard, SanitizationLevel, GuardDecision
    assert LLMGuard is not None
    assert SanitizationLevel is not None
    assert GuardDecision is not None

def test_basic_usage():
    """Verify basic dummy usage of LLMGuard."""
    from aegisai_guard import LLMGuard, SanitizationLevel
    guard = LLMGuard(sanitization_level=SanitizationLevel.MEDIUM)
    result = guard.guard("test prompt")
    assert result["decision"] == "allow"
    assert result["sanitized_text"] == "test prompt"
