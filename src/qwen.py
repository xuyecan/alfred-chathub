import json
from typing import Tuple
from llm_service import LLMService

class QwenService(LLMService):
    def construct_curl_command(self, max_tokens, messages, stream_file) -> list:
        data = {
            "model": self.model,
            "input": {
                "messages": messages,
            },
            "parameters": {
                "result_format": "message",
                "incremental_output": True,
            }
        }

        return [
            "curl",
            f"{self.api_endpoint}/api/v1/services/aigc/text-generation/generation",
            "--speed-limit", "0", "--speed-time", "5",  # Abort stalled connection after a few seconds
            "--silent", "--no-buffer",
            "--header", f"User-Agent: {self.user_agent}",
            "--header", f"Authorization: Bearer {self.api_key}",
            "--header", "Content-Type: application/json",
            "--header", "X-DashScope-SSE: enable",
            "--data", json.dumps(data),
            "--output", stream_file
        ] + self.proxy_option

    def parse_stream_response(self, stream_string) -> Tuple[str, str, bool]:
        if stream_string.strip().startswith("{"):
            response = json.loads(stream_string)
            return response.get("message", ""), response.get("code", "Unknown Error"), True

        lines = stream_string.strip().split("\n")

        chunks = []
        current_event = {}

        for line in lines:
            if line.startswith("event:"):
                current_event = {}
                current_event['event'] = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
                try:
                    current_event['data'] = json.loads(data)
                except json.JSONDecodeError as e:
                    current_event['data'] = None
                chunks.append(current_event)

        response_text = ""
        error_message = None
        has_stopped = False
        for current_event in chunks:
            if current_event['event'] == "result":
                response_text = response_text + current_event['data'].get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                finish_reason = current_event['data'].get("output", {}).get("choices", [{}])[0].get("finish_reason", "null")
                if finish_reason == "stop":
                    has_stopped = True
                    break
            elif current_event['event'] == "error":
                has_stopped = True
                error_message = current_event['data'].get("message", "Unknown Error")
                break

        return response_text, error_message, has_stopped
