import json
import subprocess
from typing import Tuple
from helper import write_file, os

from llm_service import LLMService

class AnthropicService(LLMService):
    def construct_curl_command(self, max_tokens, messages, stream_file, system_prompt) -> list:
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "stream": True
        }

        if system_prompt:
            data["system"] = system_prompt

        return [
            "curl",
            f"{self.api_endpoint}/v1/messages",
            "--speed-limit", "0", "--speed-time", "5",  # Abort stalled connection after a few seconds
            "--silent", "--no-buffer",
            "--header", "Content-Type: application/json",
            "--header", f"User-Agent: {self.user_agent}",
            "--header", f"x-api-key: {self.api_key}",
            "--header", "anthropic-version: 2023-06-01",
            "--data", json.dumps(data),
            "--output", stream_file
        ] + self.proxy_option

    def parse_stream_response(self, stream_string) -> Tuple[str, str, bool]:
        if stream_string.startswith("{"):
            try:
                error_type = json.loads(stream_string).get("error", {}).get("type", "Unknown Error")
                error_message = json.loads(stream_string).get("error", {}).get("message", "Unknown Error")
                return "", f"{error_type}: {error_message}", True
            except:
                return "", "Response body is not valid json.", True

        lines = stream_string.strip().split("\n")

        chunks = []
        current_event = {}

        for line in lines:
            if line.startswith("event:"):
                current_event = {}
                current_event['event'] = line[len("event: "):].strip()
            elif line.startswith("data:"):
                data = line[len("data: "):].strip()
                try:
                    current_event['data'] = json.loads(data)
                except json.JSONDecodeError as e:
                    current_event['data'] = None
                chunks.append(current_event)

        response_text = ""
        finish_reason = None
        has_stopped = False
        for current_event in chunks:
            if current_event['event'] == "content_block_start":
                response_text = response_text + current_event['data'].get("content_block", {}).get("text", "")
            elif current_event['event'] == "content_block_delta":
                response_text = response_text + current_event['data'].get("delta", {}).get("text", "")
            elif current_event['event'] == "message_stop":
                has_stopped = True
                finish_reason = "Finished"
                break
            elif current_event['event'] == "error":
                has_stopped = True
                finish_reason = current_event['data'].get("error", {}).get("type", "Unknown")
                break

        error_message = None
        if finish_reason == "overloaded_error":
            error_message = "Anthropic’s API is temporarily overloaded."
        elif finish_reason == "rate_limit_error":
            error_message = "Your account has hit a rate limit."
        elif finish_reason == "api_error":
            error_message = " An unexpected error has occurred internal to Anthropic’s systems."

        return response_text, error_message, has_stopped

    def start_stream(self, max_tokens, system_prompt, context_chat, stream_file, pid_stream_file):
        write_file(stream_file, "")

        while len(context_chat) > 0 and context_chat[0]["role"] == "assistant":
            context_chat.pop(0)

        curl_command = self.construct_curl_command(max_tokens, context_chat, stream_file, system_prompt)

        with open(os.devnull, 'w') as devnull:
            process = subprocess.Popen(curl_command, stdout=devnull, stderr=devnull)

        write_file(pid_stream_file, str(process.pid))
