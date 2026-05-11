import pytest
from unittest.mock import patch, MagicMock, call
from openai import APIError

from app.modules.llm.llm_client import LLMClient


class TestLLMClient:
    def test_missing_api_key_raises_valueerror(self):
        with patch("app.modules.llm.llm_client.settings") as mock_settings:
            mock_settings.LLM_API_KEY = None
            mock_settings.LLM_BASE_URL = None
            mock_settings.LLM_MODEL = "gpt-4"
            with pytest.raises(ValueError, match="LLM_API_KEY is not set"):
                LLMClient()

    def test_successful_call_returns_response_text(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Hello world"

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.modules.llm.llm_client.settings") as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = None
            mock_settings.LLM_MODEL = "gpt-4"

            with patch("app.modules.llm.llm_client.OpenAI", return_value=mock_client):
                client = LLMClient(api_key="test-key")
                result = client.call("Hi")

        assert result == "Hello world"
        mock_client.chat.completions.create.assert_called_once()

    def test_api_error_retries_and_succeeds(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Success"

        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            APIError("Rate limit", request=mock_request, body=None),
            mock_response,
        ]

        with patch("app.modules.llm.llm_client.settings") as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = None
            mock_settings.LLM_MODEL = "gpt-4"

            with patch("app.modules.llm.llm_client.OpenAI", return_value=mock_client):
                client = LLMClient(api_key="test-key")
                result = client.call("Hi", retry_delay=0.1)

        assert result == "Success"
        assert mock_client.chat.completions.create.call_count == 2

    def test_three_consecutive_api_errors_raises(self):
        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.chat.completions.create.side_effect = APIError(
            "Server error", request=mock_request, body=None
        )

        with patch("app.modules.llm.llm_client.settings") as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = None
            mock_settings.LLM_MODEL = "gpt-4"

            with patch("app.modules.llm.llm_client.OpenAI", return_value=mock_client):
                client = LLMClient(api_key="test-key")
                with pytest.raises(Exception, match="failed after 3 attempts"):
                    client.call("Hi", retry_delay=0.1)

        assert mock_client.chat.completions.create.call_count == 3

    def test_exponential_backoff_increases(self):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "OK"

        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            APIError("Fail", request=mock_request, body=None),
            mock_response,
        ]

        sleep_times = []
        original_sleep = __import__("time").sleep

        def mock_sleep(delay):
            sleep_times.append(delay)
            original_sleep(0.01)

        with patch("app.modules.llm.llm_client.settings") as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = None
            mock_settings.LLM_MODEL = "gpt-4"

            with patch("app.modules.llm.llm_client.OpenAI", return_value=mock_client):
                with patch("time.sleep", mock_sleep):
                    client = LLMClient(api_key="test-key")
                    client.call("Hi", retry_delay=1.0)

        assert len(sleep_times) == 1
        assert sleep_times[0] >= 1.0

    def test_stream_yields_chunks(self):
        chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=""))]),
        ]
        mock_stream = iter(chunks)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_stream

        with patch("app.modules.llm.llm_client.settings") as mock_settings:
            mock_settings.LLM_API_KEY = "test-key"
            mock_settings.LLM_BASE_URL = None
            mock_settings.LLM_MODEL = "gpt-4"

            with patch("app.modules.llm.llm_client.OpenAI", return_value=mock_client):
                client = LLMClient(api_key="test-key")
                result = list(client.stream("Hi"))

        assert result == ["Hello", " world"]