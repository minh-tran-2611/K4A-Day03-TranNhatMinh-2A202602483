# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Trần Nhật Minh
> **Mã Sinh Viên / Mã Học viên:** 2A202602483
> **Chủ đề Lựa chọn:** Trợ lý Học vụ Sinh viên VinUni

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Yêu cầu phức hợp cần tra cứu hồ sơ, xác định cố vấn rồi mới đặt lịch. |
| **2. Tool Interaction** | 5 / 5 | Agent bắt buộc truy cập dữ liệu học vụ và dịch vụ đặt lịch qua MCP Server. |
| **3. Dynamic Decision** | 5 / 5 | Tên cố vấn và việc có tiếp tục đặt lịch phụ thuộc trực tiếp vào kết quả tra cứu. |
| **4. Long Horizon Goal** | 3 / 5 | Agent giữ mục tiêu qua vài bước trong một phiên, nhưng không cần vận hành dài ngày. |
| **TỔNG ĐIỂM AGENTIC FIT** | **17 / 20** | Điểm số trên ngưỡng 12/20; bài toán phù hợp triển khai Agentic System. |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
  {
    "step": 1,
    "query": "Tra cứu hồ sơ sinh viên SV2026001 để xác định cố vấn, sau đó đặt lịch tư vấn với cố vấn đó vào 09:30 ngày 18/09/2026.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "academic_query",
    "arguments": {
      "student_id": "SV2026001"
    },
    "observation": {
      "status": "SUCCESS",
      "student_id": "SV2026001",
      "data": {
        "full_name": "Nguyễn Văn An",
        "gpa": 3.85,
        "advisor": "PGS.TS Nguyễn Văn A"
      }
    },
    "latency_ms": 0.0
  },
  {
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "schedule_appointment",
    "arguments": {
      "student_id": "SV2026001",
      "datetime_str": "09:30 18/09/2026",
      "advisor_name": "PGS.TS Nguyễn Văn A"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026001-99"
    }
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [ ] Đã điền API Key thật trong `.env` và xác nhận Agent chạy trên LLM API thật (cần chủ repo cung cấp API key trước khi nghiệm thu live).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases (Mock Offline).
- **Số lượt gọi Tool qua MCP Server chính xác:** 5 lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
