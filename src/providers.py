"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        student_match = re.search(r"\bsv\d{7}\b", prompt, re.IGNORECASE)
        student_id = student_match.group(0).upper() if student_match else None
        date_match = re.search(r"\b\d{1,2}:\d{2}(?:\s+(?:ngày\s+)?)?\d{1,2}/\d{1,2}/\d{4}\b", prompt, re.IGNORECASE)
        datetime_str = re.sub(r"\s+ngày\s+", " ", date_match.group(0), flags=re.IGNORECASE) if date_match else "14:00 15/09/2026"
        has_observation = "[observation" in prompt_lower
        academic_done = '"data"' in prompt and '"advisor"' in prompt
        appointment_done = '"booking_id"' in prompt
        web_done = '"results"' in prompt and '"link"' in prompt
        
        # Mô phỏng nhận diện intent gọi Tool
        if web_done:
            content = "Đã tìm thấy các kết quả web cập nhật; xem nguồn trong Waterfall Trace."
            try:
                observation_text = prompt.rsplit("]\n", 1)[-1].split("\nHãy quyết định", 1)[0]
                observation = json.loads(observation_text)
                results = observation.get("results", [])[:3]
                if results:
                    lines = [
                        f"{index}. {item.get('title', 'Không có tiêu đề')}: "
                        f"{item.get('snippet', 'Không có mô tả')} ({item.get('link', '')})"
                        for index, item in enumerate(results, 1)
                    ]
                    content = "Kết quả tìm kiếm web:\n" + "\n".join(lines)
            except (json.JSONDecodeError, AttributeError):
                pass
            return {
                "type": "text",
                "source": "mock",
                "content": content,
                "thought": "Đã nhận kết quả SerpApi nên có thể tổng hợp câu trả lời."
            }
        web_intents = (
            "tìm kiếm trên web", "tìm trên web", "search web", "internet",
            "thời tiết", "dự báo", "mưa", "nắng", "nhiệt độ"
        )
        if any(term in prompt_lower for term in web_intents) and not has_observation:
            original_query = prompt.split("\n", 1)[0].strip()
            return {
                "type": "tool_call",
                "source": "mock",
                "tool_name": "web_search",
                "arguments": {"query": original_query},
                "thought": "Yêu cầu cần thông tin trên Internet; tôi sẽ gọi web_search qua SerpApi."
            }
        if appointment_done:
            message_match = re.search(r'"message"\s*:\s*"([^"]+)"', prompt)
            return {
                "type": "text",
                "source": "mock",
                "content": message_match.group(1) if message_match else "Đã đặt lịch tư vấn học vụ thành công.",
                "thought": "Đã có xác nhận đặt lịch từ MCP Server, tôi có thể kết thúc tác vụ."
            }
        if has_observation and not ("sau đó" in prompt_lower and academic_done):
            name_match = re.search(r'"full_name"\s*:\s*"([^"]+)"', prompt)
            gpa_match = re.search(r'"gpa"\s*:\s*([\d.]+)', prompt)
            advisor_match = re.search(r'"advisor"\s*:\s*"([^"]+)"', prompt)
            content = "Đã nhận được kết quả từ hệ thống học vụ."
            if name_match:
                content = (
                    f"Sinh viên {name_match.group(1)} ({student_id}) có GPA {gpa_match.group(1) if gpa_match else 'chưa rõ'}; "
                    f"cố vấn học tập: {advisor_match.group(1) if advisor_match else 'chưa rõ'}."
                )
            return {
                "type": "text",
                "source": "mock",
                "content": content,
                "thought": "Đã có dữ liệu cần thiết từ MCP Server, tôi có thể trả lời."
            }
        if student_id and "đặt lịch" in prompt_lower and not ("tra cứu" in prompt_lower and not academic_done):
            advisor_match = re.search(r'"advisor"\s*:\s*"([^"]+)"', prompt)
            advisor = advisor_match.group(1) if advisor_match else "PGS.TS Nguyễn Văn A"
            return {
                "type": "tool_call",
                "source": "mock",
                "tool_name": "schedule_appointment",
                "arguments": {"student_id": student_id, "datetime_str": datetime_str, "advisor_name": advisor},
                "thought": f"Tôi đã đủ thông tin để đặt lịch cho {student_id}; gọi schedule_appointment."
            }
        elif student_id or "tra cứu" in prompt_lower:
            return {
                "type": "tool_call",
                "source": "mock",
                "tool_name": "academic_query",
                "arguments": {"student_id": student_id or "SV2026001"},
                "thought": f"Người dùng muốn tra cứu thông tin học vụ của {student_id or 'SV2026001'}. Tôi sẽ gọi academic_query."
            }
        else:
            return {
                "type": "text",
                "source": "mock",
                "content": f"[Mock Agent Response]: Xin chào! Quy chế học vụ VinUni yêu cầu sinh viên tích lũy tối thiểu 120 tín chỉ và duy trì GPA trên 2.0 để tốt nghiệp.",
                "thought": "Câu hỏi chung về quy chế học vụ, trả lời trực tiếp không cần gọi Tool."
            }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-3.6-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                ),
            )
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "source": "gemini_live",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "source": "gemini_live",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            fallback = MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
            fallback["source"] = "mock_fallback"
            fallback["fallback_reason"] = str(e)
            return fallback


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "source": "openai_live",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "source": "openai_live",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            fallback = MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
            fallback["source"] = "mock_fallback"
            fallback["fallback_reason"] = str(e)
            return fallback


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
