# Hướng dẫn thực hành Lab #3: Chatbot Baseline và ReAct Agent

Bài lab so sánh một chatbot trả lời một lượt không dùng công cụ với agent tra cứu dữ liệu qua registry. Dự án dùng Python 3.11; dữ liệu trong raw-data là dữ liệu mẫu, không phải thông tin thời gian thực.

## Chuẩn bị môi trường

Từ thư mục VinUni_Codelab_Day03_Template, môi trường ảo đã có sẵn. Kiểm tra bằng:

~~~powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest autograder tests -v
~~~

Nếu muốn thử Gemini API, mở file .env ở thư mục này và điền GEMINI_API_KEY. Để trống vẫn chạy được toàn bộ agent và autograder. Không đưa API key vào mã nguồn hoặc commit file .env.

## Milestone 1 — Chatbot Baseline

ChatbotBaseline nằm trong starter-code/template.py. Constructor nhận api_key tùy chọn; nếu không truyền, nó đọc GEMINI_API_KEY từ môi trường hoặc .env. Phương thức query(user_input) luôn trả một dictionary có answer, tool_calls, status và mode.

- Có key và API hoạt động: mode=live_api, một lượt gọi gemini-2.5-flash, tool_calls=[].
- Không có key hoặc truyền api_key="" để chạy offline: mode=mock_baseline, fallback_reason=no_api_key.
- API lỗi hoặc trả nội dung rỗng: mode=mock_baseline, fallback_reason cho biết loại lỗi nhưng không chứa key.

Baseline không tra cứu dữ liệu chuyến bay hoặc thời tiết. Vì thế câu trả lời của nó không nên được xem là thông tin đã xác minh. Mã dùng SDK google-genai hiện được Google duy trì thay cho google-generativeai cũ. [Tài liệu SDK chính thức](https://ai.google.dev/gemini-api/docs/libraries).

Thử nhanh:

~~~powershell
.\.venv\Scripts\python.exe starter-code\template.py
~~~

Trong kết quả CHATBOT BASELINE, kiểm tra tool_calls là mảng rỗng và mode cho biết chế độ đang chạy. Khi .env để trống, mode sẽ là mock_baseline.

## Milestone 2 — Tool Registry

starter-code/tools.py khai báo hai công cụ và ánh xạ TOOL_MAP:

- get_flight_info(origin, destination, max_price): lọc raw-data/flight_data.json.
- get_weather_forecast(city_code): đọc raw-data/weather_data.json.

Ví dụ với HAN → SGN, ngân sách 2.000.000 VND, công cụ trả VN213 và VJ151. Thời tiết SGN trong dữ liệu mẫu là 32°C kèm gợi ý trang phục. Những dữ liệu này chỉ phục vụ bài lab.

## Milestone 3 — Vòng lặp ReAct

ReActAgent hiện dùng bộ lập kế hoạch cố định để nhận diện câu hỏi, không gọi Gemini. Với câu hỏi về vé và thời tiết, agent tạo Action cho từng công cụ, thực thi qua TOOL_MAP, ghi Observation vào trace rồi tổng hợp Final Answer.

~~~text
User → Thought → Action(get_flight_info) → Observation
     → Thought → Action(get_weather_forecast) → Observation
     → Thought → Final Answer
~~~

Mỗi trace step lưu iteration, thought, action, observation; bước cuối có final_answer. Câu hỏi chỉ cần một công cụ kết thúc trong một bước. Câu hỏi chính sách không có dữ liệu trong repo sẽ không gọi công cụ và không tự nêu quy định hoặc mức phí.

## Milestone 4 — Safeguards và kiểm thử

Agent giới hạn max_iterations, làm mới trace ở đầu mỗi lần run(), chuẩn hóa tên Action bằng strip().lower(), kiểm tra tên công cụ trong TOOL_MAP và chuyển lỗi công cụ thành Observation. Nếu hết lượt trước khi hoàn thành, status là max_iterations_reached.

Chạy toàn bộ bài kiểm tra:

~~~powershell
.\.venv\Scripts\python.exe -m pytest autograder tests -v
~~~

Autograder có 8 bài; tests/test_baseline.py bổ sung kiểm tra nhánh Gemini giả lập, fallback và việc không đoán tuyến bay/chính sách. Không cần API key thật để chạy kiểm thử.

## Các lỗi thường gặp

1. mode vẫn là mock_baseline: kiểm tra GEMINI_API_KEY trong .env tại thư mục gốc và fallback_reason; nếu key sai hoặc mạng/API lỗi, baseline dùng câu trả lời mẫu.
2. Nhầm dữ liệu mẫu với dữ liệu trực tiếp: tools.py chỉ đọc JSON trong repo. Không dùng kết quả này để đặt vé hoặc dự báo thời tiết thực tế.
3. Chạy bằng Python MSYS trong PATH: môi trường ảo của dự án dùng Python Windows, nên gọi trực tiếp .venv/Scripts/python.exe như các lệnh phía trên.
