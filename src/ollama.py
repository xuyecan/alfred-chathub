import json
from typing import Optional

from llm_service import LLMService


class OllamaService(LLMService):
    def __init__(self, api_endpoint, model, http_proxy, socks5_proxy):
        super().__init__(api_endpoint, "", model, http_proxy, socks5_proxy)

    def construct_curl_command(self, max_tokens, messages, stream_file):
        data = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"num_predict": max_tokens},
        }

        return [
            "curl",
            f"{self.api_endpoint}/api/chat",
            "--speed-limit",
            "0",
            "--speed-time",
            str(self.stall_timeout_sec),  # Abort stalled connection after a few seconds
            "--silent",
            "--no-buffer",
            "--header",
            "Content-Type: application/json",
            "--data",
            json.dumps(data),
            "--output",
            stream_file,
        ] + self.proxy_option

    def parse_stream_response(self, stream_string) -> tuple[str, Optional[str], bool]:
        response_text = ""
        has_stopped = False

        for line in stream_string.split("\n"):
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                # 忽略不完整分片，避免误报
                continue

            # 统一错误呈现：Ollama 在失败时可能返回 {"error": "..."}
            if "error" in chunk and chunk["error"]:
                return str(chunk["error"]), "", True

            if "message" in chunk:
                response_text += chunk["message"].get("content", "")
            if "done" in chunk and chunk["done"]:
                has_stopped = True

        return response_text, None, has_stopped
