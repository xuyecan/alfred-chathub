import json
from typing import Tuple

from llm_service import LLMService

class GeminiService(LLMService):
    def construct_curl_command(self, max_tokens, messages, stream_file) -> list:
        """
        message here:
        [
            {"role": "system", "content": "You are a chatbot."},
            {"role": "user", "content": "hello, there!"},
            {"role": "assistant", "content": "Hello! How can I help you today?"}
        ]
        """
        content = [{"parts": [{"text": message["content"]}], "role": "model" if message["role"] == "assistant" else message["role"]} for message in messages]
        data = {
            "contents": content,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                # "temperature": 0.8
            }
        }

        return [
            "curl",
            f"{self.api_endpoint}/v1/models/{self.model}:streamGenerateContent?key={self.api_key}",
            "--speed-limit", "0", "--speed-time", "5",  # Abort stalled connection after a few seconds
            "--silent", "--no-buffer",
            "--header", f"User-Agent: {self.user_agent}",
            "--header", "Content-Type: application/json",
            "--data", json.dumps(data),
            "--output", stream_file
        ] + self.proxy_option

    def read_and_split_file(self, stream_string):
        parts = []
        current_part = []
    
        lines = stream_string.strip().split("\n")
        for line in lines:
            if line.strip() == ",":
                if current_part:
                    parts.append("".join(current_part).strip())
                    current_part = []
            else:
                current_part.append(line)

        if current_part:  # Append the last part if exists
            parts.append("".join(current_part).strip())

        has_stopped = False
        processed_parts = []
        for part in parts:
            if part.startswith('['):
                part = part[1:]
            if part.endswith(']'):
                part = part[:-1]
                has_stopped = True
            processed_parts.append(part)
        return processed_parts, has_stopped

    def parse_stream_response(self, stream_string) -> Tuple[str, str, bool]:
        if stream_string.strip().startswith("{"):
            response = json.loads(stream_string)
            error_message = response.get("error", {}).get("message", "Unknown Error")
            return "", error_message, True

        parts, has_stopped = self.read_and_split_file(stream_string)

        chunks = []
        current_event = {}

        for part in parts:
            try:
                current_event = json.loads(part)
            except json.JSONDecodeError as e:
                continue
            chunks.append(current_event)

        response_text = ""
        error_message = None
        for current_event in chunks:
            candidates = current_event.get("candidates", [])
            first_candidate = candidates[0] if len(candidates) > 0 else {}
            content = first_candidate.get("content", {})
            parts = content.get("parts", [])
            first_part = parts[0] if len(parts) > 0 else {}
            response_text += first_part.get("text", "")
        return response_text, error_message, has_stopped