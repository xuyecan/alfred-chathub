#!/usr/bin/env python3

import json
import tempfile
import time
from typing import Optional, Tuple

from llm_service import LLMService


class DeepseekService(LLMService):
    def construct_curl_command(self, max_tokens, messages, stream_file) -> list:
        max_tokens = min(max(1, max_tokens), 8192)  # deepseek limit up to 8192

        data = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
        }

        return [
            "curl",
            f"{self.api_endpoint}/v1/chat/completions",
            "--speed-limit",
            "0",
            "--speed-time",
            str(self.stall_timeout_sec),
            "--silent",
            "--no-buffer",
            "--header",
            f"User-Agent: {self.user_agent}",
            "--header",
            "Content-Type: application/json",
            "--header",
            f"Authorization: Bearer {self.api_key}",
            "--data",
            json.dumps(data),
            "--output",
            stream_file,
        ] + self.proxy_option

    def parse_stream_response(self, stream_string) -> Tuple[str, Optional[str], bool]:
        # 针对 Deepseek 的 OpenAI 兼容流：既可能返回一次性 JSON 错误体，也可能在 SSE 分片中夹带错误对象。
        # 统一策略：遇到服务端错误时直接回显可读信息，不再走 footer 错误路径。
        if stream_string.startswith("{"):
            try:
                obj = json.loads(stream_string)
            except Exception:
                return "Response body is not valid json.", "", True

            err = obj.get("error")
            if err is not None:
                message = err.get("message") if isinstance(err, dict) else str(err)
                return (message or json.dumps(err, ensure_ascii=False)), "", True

            choices = obj.get("choices")
            if isinstance(choices, list) and len(choices) > 0:
                # Deepseek-Reasoner 可能返回 content=None（思维片段在 reasoning_content），需做 None 安全处理
                msg_content = choices[0].get("message", {}).get("content")
                if msg_content is None:
                    msg_content = choices[0].get("delta", {}).get("content")
                content = msg_content if isinstance(msg_content, str) else ""
                finish_reason = choices[0].get("finish_reason")
                return content, "", True if finish_reason else False

            return json.dumps(obj, ensure_ascii=False), "", True

        raw_chunks = []
        error_from_sse = None
        for line in stream_string.split("\n"):
            if not line.startswith("data: "):
                continue
            data_str = line[len("data: ") :].strip()
            if data_str == "[DONE]":
                continue
            try:
                obj = json.loads(data_str)
                if (
                    isinstance(obj, dict)
                    and obj.get("error") is not None
                    and error_from_sse is None
                ):
                    error_from_sse = obj.get("error")
                raw_chunks.append(obj)
            except json.JSONDecodeError:
                continue

        valid_chunks = []
        for obj in raw_chunks:
            choices = obj.get("choices")
            if isinstance(choices, list) and len(choices) > 0:
                valid_chunks.append(obj)

        if error_from_sse is not None:
            if isinstance(error_from_sse, dict):
                message = error_from_sse.get("message") or json.dumps(
                    error_from_sse, ensure_ascii=False
                )
            else:
                message = str(error_from_sse)
            return message, "", True

        # 累积可见文本片段；忽略 reasoning_content，以避免在 UI 中输出“思维过程”
        pieces = []
        for c in valid_chunks:
            delta = c["choices"][0].get("delta", {})
            text = delta.get("content")
            if text is None or not isinstance(text, str):
                text = ""
            pieces.append(text)
        response_text = "".join(pieces)

        finish_reason = None
        if valid_chunks:
            finish_reason = valid_chunks[-1]["choices"][0].get("finish_reason")

        error_message = None
        has_stopped = False
        if finish_reason is None:
            has_stopped = False
        elif finish_reason == "stop":
            has_stopped = True
        elif finish_reason == "length":
            has_stopped = True
            error_message = "The response reached the maximum token limit."
        elif finish_reason == "content_filter":
            has_stopped = True
            error_message = "The response was flagged by the content filter."
        else:
            has_stopped = True
            error_message = "Unknown Error"

        return response_text, error_message, has_stopped


def test_deepseek():
    api_endpoint = "https://api.deepseek.com"
    api_key = "your_api_key"
    model = "deepseek-chat"

    service = DeepseekService(api_endpoint, api_key, model, "", "")

    with (
        tempfile.NamedTemporaryFile(mode="w+", delete=False) as stream_file,
        tempfile.NamedTemporaryFile(mode="w+", delete=False) as pid_file,
    ):
        messages = [
            {"role": "user", "content": "Hello, can you tell me about yourself?"}
        ]

        service.start_stream(1000, "", messages, stream_file.name, pid_file.name)

        print("Waiting for response...")
        while True:
            with open(stream_file.name, "r", encoding="utf-8") as f:
                response = f.read()
                if response:
                    response_text, error_message, has_stopped = (
                        service.parse_stream_response(response)
                    )
                    if error_message:
                        print(f"Error: {error_message}")
                        break
                    if has_stopped:
                        print(f"Response: {response_text}")
                        break
            time.sleep(0.1)

        import os

        os.unlink(stream_file.name)
        os.unlink(pid_file.name)


if __name__ == "__main__":
    test_deepseek()
