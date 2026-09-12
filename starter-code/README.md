# Lab #3: Chatbot Baseline và ReAct Agent

Python 3.11 và các thư viện đã được cài trong môi trường ảo ở thư mục gốc dự án. Từ VinUni_Codelab_Day03_Template, chạy:

~~~powershell
.\.venv\Scripts\python.exe starter-code\template.py
.\.venv\Scripts\python.exe -m pytest autograder tests -v
~~~

Để cài lại dependency vào môi trường ảo:

~~~powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
uv pip install --python .venv\Scripts\python.exe -r starter-code\requirements.txt
~~~

## Dùng Gemini API (tùy chọn)

Điền key vào file .env ở thư mục gốc dự án:

~~~dotenv
GEMINI_API_KEY=key_cua_ban
~~~

Không chia sẻ hoặc commit file .env; .gitignore đã loại trừ file này. ChatbotBaseline ưu tiên api_key truyền trực tiếp, rồi tới GEMINI_API_KEY trong môi trường hoặc .env. Truyền api_key="" để cố ý chạy offline, kể cả khi .env có key. Có key, baseline gọi gemini-2.5-flash qua google-genai và trả mode=live_api. Không có key hoặc API lỗi, baseline trả mode=mock_baseline; fallback_reason cho biết lý do. Baseline luôn trả tool_calls=[].

ReActAgent là agent lập kế hoạch cố định, chạy không cần API key. Agent dùng get_flight_info và get_weather_forecast từ tools.py để đọc raw-data. Đây là dữ liệu mẫu, không phải chuyến bay hoặc dự báo thời tiết trực tiếp. Câu hỏi về chính sách không có nguồn trong repo sẽ được báo là chưa xác thực.

Chi tiết từng bước nằm trong student_guide.md.
