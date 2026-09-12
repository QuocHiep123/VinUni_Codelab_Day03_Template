import sys
from pathlib import Path
from types import SimpleNamespace

from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter-code"))
import template
from template import ChatbotBaseline, ReActAgent


def test_baseline_live_api_uses_gemini_without_tools(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        @property
        def models(self):
            return self

        def generate_content(self, *, model, contents, config):
            calls.append((model, contents, config))
            return SimpleNamespace(text="Đây là câu trả lời thử.")

    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(
        genai=SimpleNamespace(Client=FakeClient)))
    result = ChatbotBaseline(api_key="test-key").query("Tư vấn du lịch")

    assert result == {
        "answer": "Đây là câu trả lời thử.",
        "tool_calls": [],
        "status": "success",
        "mode": "live_api",
    }
    assert len(calls) == 1
    assert calls[0][0] == "gemini-2.5-flash"
    assert "Tư vấn du lịch" in calls[0][1]
    assert calls[0][2].automatic_function_calling.disable is True


def test_baseline_falls_back_without_key(monkeypatch):
    result = ChatbotBaseline(api_key="").query("Tìm chuyến bay")

    assert result["mode"] == "mock_baseline"
    assert result["fallback_reason"] == "no_api_key"
    assert result["tool_calls"] == []


def test_baseline_reads_key_from_dotenv(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(template, "dotenv_values", lambda path: {
        "GEMINI_API_KEY": "file-key"})

    assert ChatbotBaseline().api_key == "file-key"


def test_baseline_reports_api_fallback_without_exposing_key(monkeypatch):
    class BrokenClient:
        def __init__(self, api_key):
            raise RuntimeError("private test-key")

    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(
        genai=SimpleNamespace(Client=BrokenClient)))
    result = ChatbotBaseline(api_key="test-key").query("Tìm chuyến bay")

    assert result["mode"] == "mock_baseline"
    assert result["fallback_reason"] == "api_error:RuntimeError"
    assert "test-key" not in str(result)


def test_react_does_not_guess_route_or_policy():
    agent = ReActAgent()
    flights = agent.run("Tìm chuyến bay từ SGN đi HAN dưới 500k.")
    assert flights["trace"][0]["action"]["args"]["origin"] == "SGN"
    assert flights["trace"][0]["action"]["args"]["destination"] == "HAN"
    assert "Không tìm thấy" in flights["answer"]

    policy = agent.run("Chính sách đổi trả vé máy bay Vinpearl như thế nào?")
    assert all(step["action"] is None for step in policy["trace"])
    assert "chưa có dữ liệu xác thực" in policy["answer"]
