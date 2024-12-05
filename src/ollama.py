import json
from llm_service import LLMService

class OllamaService(LLMService):
    def __init__(self, api_endpoint, model, http_proxy, socks5_proxy):
        super().__init__(api_endpoint, "", model, http_proxy, socks5_proxy)

    def construct_curl_command(self, max_tokens, messages, stream_file):
        data = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_predict": max_tokens
            },
        }

        return [
            "curl",
            f"{self.api_endpoint}/api/chat",
            "--speed-limit", "0", "--speed-time", "5",  # Abort stalled connection after a few seconds
            "--silent", "--no-buffer",
            "--header", "Content-Type: application/json",
            "--data", json.dumps(data),
            "--output", stream_file
        ] + self.proxy_option

    def parse_stream_response(self, stream_string):
        response_text = ""
        error_message = ""
        has_stopped = False

        for line in stream_string.split("\n"):
            if line.strip():
                try:
                    chunk = json.loads(line)
                    if 'message' in chunk:
                        response_text += chunk['message']['content']
                    if 'done' in chunk and chunk['done']:
                        has_stopped = True
                except json.JSONDecodeError:
                    error_message = "Error parsing JSON response"

        return response_text, error_message, has_stopped
