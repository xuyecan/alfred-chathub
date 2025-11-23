import json
from typing import Optional, Tuple

from llm_service import LLMService


class OpenaiService(LLMService):
    def construct_curl_command(self, max_tokens, messages, stream_file) -> list:
        """
        message here:
        [
            {"role": "system", "content": "You are a chatbot."},
            {"role": "user", "content": "hello, there!"},
            {"role": "assistant", "content": "Hello! How can I help you today?"}
        ]
        """
        data = {"model": self.model, "messages": messages, "stream": True}

        return [
            "curl",
            f"{self.api_endpoint}/v1/chat/completions",
            "--speed-limit",
            "0",
            "--speed-time",
            str(self.stall_timeout_sec),  # Abort stalled connection after a few seconds
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
        # 当响应不是 SSE 流（不以 data: 开头）时，可能是错误或非流式一次性响应。
        # 为了“直接展示错误信息”，这里优先解析错误对象；若是一次性成功响应则回退到正常内容解析。
        if stream_string.startswith("{"):
            try:
                obj = json.loads(stream_string)
            except Exception:
                # 原样回显非 JSON 的错误体，便于用户定位问题
                return stream_string.strip(), "", True

            # 1) 标准/兼容 OpenAI 错误格式：{"error": {"message": "...", "type": "...", ...}}
            err = obj.get("error")
            if err is not None:
                # 直接回显服务端 message；若缺失则回显序列化后的错误对象
                message = err.get("message") if isinstance(err, dict) else str(err)
                return (message or json.dumps(err, ensure_ascii=False)), "", True

            # 2) 某些兼容实现可能返回一次性完成对象（非流式），这里尽量提取内容
            choices = obj.get("choices")
            if isinstance(choices, list) and len(choices) > 0:
                content = (
                    choices[0].get("message", {}).get("content")
                    or choices[0].get("delta", {}).get("content")
                    or ""
                )
                finish_reason = choices[0].get("finish_reason")
                # 将其视作已完成；不设置 error_message，UI 将直接显示内容
                return content, "", True if finish_reason else False

            # 3) 其他未知 JSON：原样回显，确保用户能直接看到返回体
            return json.dumps(obj, ensure_ascii=False), "", True

        raw_chunks = []
        error_from_sse = None
        saw_done = False
        for line in stream_string.split("\n"):
            if not line.startswith("data: "):
                continue
            data_str = line[len("data: ") :].strip()
            if data_str == "[DONE]":
                # 某些新模型可能不再在最后一个 choices 中给出 finish_reason，此时仅依赖 [DONE] 作为结束信号
                saw_done = True
                continue
            try:
                obj = json.loads(data_str)
                # 兼容：部分“OpenAI 兼容”服务可能通过 SSE 分片发送错误对象
                if (
                    isinstance(obj, dict)
                    and obj.get("error") is not None
                    and error_from_sse is None
                ):
                    error_from_sse = obj.get("error")
                raw_chunks.append(obj)
            except json.JSONDecodeError:
                continue

        # 兼容性处理：部分 OpenAI 兼容服务会发送不含 choices 的心跳/统计事件。
        valid_chunks = []
        for obj in raw_chunks:
            choices = obj.get("choices")
            if isinstance(choices, list) and len(choices) > 0:
                valid_chunks.append(obj)

        # 如在 SSE 流中捕获到错误对象，则直接回显错误并终止
        if error_from_sse is not None:
            if isinstance(error_from_sse, dict):
                message = error_from_sse.get("message") or json.dumps(
                    error_from_sse, ensure_ascii=False
                )
            else:
                message = str(error_from_sse)
            return message, "", True

        response_text = "".join(
            c["choices"][0].get("delta", {}).get("content", "") for c in valid_chunks
        )

        finish_reason = None
        if valid_chunks:
            finish_reason = valid_chunks[-1]["choices"][0].get("finish_reason")

        error_message = None
        has_stopped = False

        if finish_reason is None:
            # 兼容：若未给出 finish_reason，但已收到 [DONE]，则判定为完成
            has_stopped = True if saw_done else False
        elif finish_reason == "stop":
            has_stopped = True
        elif finish_reason == "end_turn":  # 向后兼容可能的别名
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
