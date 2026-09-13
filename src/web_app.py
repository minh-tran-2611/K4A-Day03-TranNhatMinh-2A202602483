"""Giao diện web so sánh LLM Chatbot và ReAct Agent (không cần framework)."""

import contextlib
import io
import json
import os
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import run_react_agent
from mcp_server import MCPAcademicServer
from prompts import CHATBOT_BASELINE_PROMPT
from providers import get_llm_provider


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(ROOT_DIR, "web")
PROVIDER = get_llm_provider()
MCP_SERVER = MCPAcademicServer()


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_POST(self):
        if self.path not in ("/api/compare", "/api/compare-stream"):
            self.send_error(404)
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size) or b"{}")
            query = str(payload.get("query", "")).strip()
            if not query:
                raise ValueError("Vui lòng nhập một câu hỏi.")
            if len(query) > 1000:
                raise ValueError("Câu hỏi tối đa 1.000 ký tự.")

            if self.path == "/api/compare-stream":
                self.run_stream(query)
                return

            baseline_start = time.perf_counter()
            baseline = PROVIDER.generate(query, system_prompt=CHATBOT_BASELINE_PROMPT)
            baseline_ms = round((time.perf_counter() - baseline_start) * 1000, 1)
            baseline_live = not baseline.startswith(("[Gemini Exception]", "[OpenAI Exception]", "[Mock"))
            agent_start = time.perf_counter()
            with contextlib.redirect_stdout(io.StringIO()):
                trace = run_react_agent(query, PROVIDER, MCP_SERVER)
            agent_ms = round((time.perf_counter() - agent_start) * 1000, 1)

            final_events = [item for item in trace if item.get("action_type") == "FINAL_ANSWER"]
            agent_answer = final_events[-1].get("output", "") if final_events else "Agent chưa tạo được câu trả lời."
            tool_calls = sum(item.get("action_type") == "TOOL_EXECUTION" for item in trace)
            sources = sorted({item.get("model_source", "") for item in trace if item.get("model_source")})
            agent_live = any(source.endswith("_live") for source in sources) and "mock_fallback" not in sources
            self.send_json(200, {
                "baseline": baseline,
                "agent": agent_answer,
                "trace": trace,
                "tool_calls": tool_calls,
                "provider": PROVIDER.__class__.__name__,
                "baseline_ms": baseline_ms,
                "agent_ms": agent_ms,
                "baseline_live": baseline_live,
                "agent_live": agent_live,
                "sources": sources,
            })
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"error": f"Không thể xử lý yêu cầu: {exc}"})

    def run_stream(self, query):
        """Gửi từng sự kiện NDJSON ngay khi mỗi bước thực sự diễn ra."""
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def emit(payload):
            self.wfile.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            self.wfile.flush()

        try:
            started = time.perf_counter()

            def progress(event):
                emit(event)

            with contextlib.redirect_stdout(io.StringIO()):
                trace = run_react_agent(query, PROVIDER, MCP_SERVER, progress_callback=progress)
            agent_ms = round((time.perf_counter() - started) * 1000, 1)
            sources = sorted({item.get("model_source", "") for item in trace if item.get("model_source")})
            agent_live = any(source.endswith("_live") for source in sources) and "mock_fallback" not in sources
            emit({
                "event": "agent_done", "trace": trace, "agent_ms": agent_ms,
                "agent_live": agent_live, "sources": sources,
                "tool_calls": sum(item.get("action_type") == "TOOL_EXECUTION" for item in trace),
                "provider": PROVIDER.__class__.__name__,
            })

            emit({"event": "llm_start"})
            started = time.perf_counter()
            baseline = PROVIDER.generate(query, system_prompt=CHATBOT_BASELINE_PROMPT)
            baseline_ms = round((time.perf_counter() - started) * 1000, 1)
            baseline_live = not baseline.startswith(("[Gemini Exception]", "[OpenAI Exception]", "[Mock"))
            emit({"event": "llm_done", "answer": baseline, "elapsed_ms": baseline_ms, "live": baseline_live})
            emit({
                "event": "done", "provider": PROVIDER.__class__.__name__,
                "trace_count": len(trace), "baseline_live": baseline_live,
            })
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            emit({"event": "error", "message": str(exc)})

    def send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[WEB] {self.address_string()} - {fmt % args}")


if __name__ == "__main__":
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "8080"))
    print(f"Mở giao diện tại http://{host}:{port}")
    ThreadingHTTPServer((host, port), DemoHandler).serve_forever()
