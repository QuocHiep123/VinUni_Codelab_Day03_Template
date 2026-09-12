"""Lab #3: baseline chatbot and a data-grounded ReAct agent.

The deterministic planner keeps this exercise runnable without an API key.
All factual answers are built from observations returned by registered tools.
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from tools import TOOL_MAP


CITY_CODES = {
    "ha noi": "HAN", "hanoi": "HAN",
    "da nang": "DAD", "danang": "DAD",
    "ho chi minh": "SGN", "sai gon": "SGN", "saigon": "SGN",
}


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def _city_codes(query: str) -> list[str]:
    plain = _plain(query)
    found = [(match.start(), match.group().upper())
             for match in re.finditer(r"\b(?:HAN|SGN|DAD)\b", query, re.I)]
    for city, code in CITY_CODES.items():
        found.extend((match.start(), code)
                     for match in re.finditer(rf"\b{re.escape(city)}\b", plain))
    ordered = [code for _, code in sorted(found)]
    return [code for index, code in enumerate(ordered)
            if index == 0 or code != ordered[index - 1]]


def _max_price(query: str) -> int:
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(triệu|trieu|tr|k|nghìn|nghin|ngàn|ngan|vnd|đồng|dong)\b",
                      query.casefold())
    if not match:
        return 5_000_000
    number = float(match.group(1).replace(",", "."))
    unit = _plain(match.group(2))
    scale = 1_000_000 if unit in {"trieu", "tr"} else 1_000 if unit in {"k", "nghin", "ngan"} else 1
    return int(number * scale)


def _plan(query: str) -> tuple[list[dict[str, Any]], str | None]:
    plain = _plain(query)
    if "chinh sach" in plain:
        brand = " Vinpearl" if "vinpearl" in plain else ""
        return [], (f"Mình chưa có dữ liệu xác thực về chính sách{brand}. "
                    "Vui lòng kiểm tra kênh hỗ trợ chính thức để có thông tin mới nhất.")
    flight = any(term in plain for term in ("chuyen bay", "ve may bay", "tim ve", "bay tu"))
    weather = any(term in plain for term in ("thoi tiet", "nhiet do", "du bao", "nen mac"))
    codes = _city_codes(query)
    actions: list[dict[str, Any]] = []
    if flight:
        if len(codes) < 2:
            return [], "Bạn vui lòng cho biết sân bay đi và đến để mình tra chuyến bay."
        actions.append({"name": "get_flight_info", "args": {
            "origin": codes[0], "destination": codes[1], "max_price": _max_price(query)}})
    if weather:
        if not codes:
            return [], "Bạn vui lòng cho biết thành phố cần xem thời tiết."
        actions.append({"name": "get_weather_forecast", "args": {"city_code": codes[-1]}})
    return actions, None


def _answer(observations: list[tuple[str, Any]], fallback: str | None = None) -> str:
    if fallback:
        return fallback
    if not observations:
        return ("Mình chưa có dữ liệu xác thực cho câu hỏi này. "
                "Vui lòng xem kênh hỗ trợ chính thức.")
    parts = []
    for name, result in observations:
        if isinstance(result, dict) and "error" in result:
            parts.append(f"Không tra cứu được dữ liệu: {result['error']}.")
        elif name == "get_flight_info":
            if not result:
                parts.append("Không tìm thấy chuyến bay phù hợp với tuyến và mức giá yêu cầu trong dữ liệu mẫu.")
            else:
                flights = "; ".join(
                    f"{item['flight_number']} ({item['airline']}), "
                    f"{item['origin']} → {item['destination']}, {item['departure_time']}, "
                    f"{item['price_vnd']:,} VND" for item in result)
                parts.append(f"Chuyến bay phù hợp: {flights}.")
        elif name == "get_weather_forecast":
            parts.append(
                f"Thời tiết trong dữ liệu mẫu tại {result['city']}: "
                f"{result['temperature_c']}°C, {result['condition']}. "
                f"Gợi ý trang phục: {result['recommendation']}")
    return " ".join(parts)


class ChatbotBaseline:
    """One-turn Gemini chatbot without tools, with an offline fallback."""

    def __init__(self, api_key: str | None = None):
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            file_key = dotenv_values(Path(__file__).resolve().parent.parent / ".env").get("GEMINI_API_KEY")
            self.api_key = (os.getenv("GEMINI_API_KEY") or file_key or "").strip()

    def query(self, user_input: str) -> dict[str, Any]:
        fallback_reason = "no_api_key"
        if self.api_key:
            try:
                from google import genai
                from google.genai import types

                with genai.Client(api_key=self.api_key) as client:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=(
                            "Bạn là chatbot tư vấn du lịch. Trả lời câu hỏi sau mà "
                            "không dùng công cụ, tìm kiếm hay dữ liệu thời gian thực. "
                            "Nếu không thể xác minh thông tin, hãy nói rõ điều đó.\n"
                            f"Câu hỏi: {user_input}"
                        ),
                        config=types.GenerateContentConfig(
                            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                                disable=True
                            )
                        ),
                    )
                answer = (response.text or "").strip()
                if not answer:
                    raise ValueError("Empty model response")
                return {
                    "answer": answer,
                    "tool_calls": [],
                    "status": "success",
                    "mode": "live_api",
                }
            except Exception as exc:
                # Keep the demo usable offline without exposing key-bearing errors.
                fallback_reason = f"api_error:{type(exc).__name__}"

        return {
            "status": "success",
            "answer": (
                "Bạn có thể tìm chuyến bay trên trang của hãng hàng không. "
                "Về thời tiết, hãy kiểm tra trang dự báo thời tiết trước khi đi."
            ),
            "tool_calls": [],
            "mode": "mock_baseline",
            "fallback_reason": fallback_reason,
        }


class ReActAgent:
    """Execute Thought → Action → Observation steps within a bounded loop."""

    def __init__(self, max_iterations: int = 5):
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        self.max_iterations = max_iterations
        self.trace: list[dict[str, Any]] = []

    def run(self, user_input: str) -> dict[str, Any]:
        self.trace = []
        actions, fallback = _plan(user_input)
        observations: list[tuple[str, Any]] = []
        if not actions:
            answer = _answer(observations, fallback)
            self.trace.append({"iteration": 1, "thought": "Không cần công cụ.",
                               "action": None, "observation": None, "final_answer": answer})
            return {"status": "completed", "answer": answer, "iterations": 1, "trace": self.trace}

        for iteration, action in enumerate(actions, start=1):
            if iteration > self.max_iterations:
                return {"status": "max_iterations_reached", "answer": _answer(observations),
                        "iterations": len(self.trace), "trace": self.trace}

            # Parse and normalize the JSON Action before consulting the registry.
            try:
                parsed = json.loads(json.dumps(action, ensure_ascii=False))
                name = parsed["name"].strip().lower()
                args = parsed["args"]
                if not isinstance(args, dict) or name not in TOOL_MAP:
                    raise ValueError("Invalid tool action")
                observation = TOOL_MAP[name](**args)
            except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
                name = action["name"]
                observation = {"error": str(exc)}

            observations.append((name, observation))
            step = {"iteration": iteration, "thought": f"Cần tra cứu bằng {name}.",
                    "action": action, "observation": observation}
            self.trace.append(step)
            if isinstance(observation, dict) and "error" in observation:
                answer = _answer(observations)
                step["final_answer"] = answer
                return {"status": "completed", "answer": answer,
                        "iterations": iteration, "trace": self.trace}

        answer = _answer(observations)
        if len(actions) > 1 and len(self.trace) < self.max_iterations:
            self.trace.append({"iteration": len(self.trace) + 1,
                               "thought": "Đã có đủ dữ liệu để trả lời.",
                               "action": None, "observation": None, "final_answer": answer})
        else:
            self.trace[-1]["final_answer"] = answer
        return {"status": "completed", "answer": answer,
                "iterations": len(self.trace), "trace": self.trace}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    query = "Tìm cho tôi chuyến bay từ HAN đi SGN dưới 2 triệu, rồi cho biết thời tiết SGN nên mặc gì?"
    print("=== CHATBOT BASELINE ===")
    print(json.dumps(ChatbotBaseline().query(query), ensure_ascii=False, indent=2))
    print("\n=== REACT AGENT ===")
    print(json.dumps(ReActAgent().run(query), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
