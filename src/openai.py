from llm_service import *

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
        data = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        return [
            "curl",
            f"{self.api_endpoint}/v1/chat/completions",
            "--speed-limit", "0", "--speed-time", "5",  # Abort stalled connection after a few seconds
            "--silent", "--no-buffer",
            "--header", f"User-Agent: {self.user_agent}",
            "--header", "Content-Type: application/json",
            "--header", f"Authorization: Bearer {self.api_key}",
            "--data", json.dumps(data),
            "--output", stream_file
        ] + self.proxy_option
    
    def parse_stream_response(self, stream_string) -> Tuple[str, str, bool]:
        if stream_string.startswith("{"):
            try:
                error_message = json.loads(stream_string).get("error", {}).get("message")
                return "", error_message, True
            except:
                return "", "Response body is not valid json.", True

        chunks = []

        for line in stream_string.split("\n"):
            if line.startswith("data: "):
                data_str = line[len("data: "):]
                try:
                    chunks.append(json.loads(data_str))
                except json.JSONDecodeError as e:
                    pass

        response_text = "".join(
            item["choices"][0].get("delta", {}).get("content", "") for item in chunks
        )

        finish_reason = chunks[-1]["choices"][0]["finish_reason"]
        error_message = None
        has_stopped = False

        if finish_reason is None:
            pass
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
