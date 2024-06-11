import os
import time
import json
import subprocess
from abc import ABC, abstractmethod
from typing import Tuple
from helper import *

class LLMService(ABC):
    def __init__(self, api_endpoint, api_key, model, http_proxy=None, socks5_proxy=None):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.model = model
        self.user_agent = "Alfred-Chathub"

        if len(http_proxy) > 0:
            self.proxy_option = ["-x", f"http://{http_proxy}"]
        elif len(socks5_proxy) > 0:
            self.proxy_option = ["--socks5-hostname", f"socks5://{socks5_proxy}"]
        else:
            self.proxy_option = []

    @abstractmethod
    def construct_curl_command(self, max_tokens, messages, stream_file) -> list:
        pass

    @abstractmethod
    def parse_stream_response(self, stream_string) -> Tuple[str, str, bool]:
        pass

    def start_stream(self, max_tokens, system_prompt, context_chat, stream_file, pid_stream_file):
        write_file(stream_file, "")  # Create empty file

        messages = [{"role": "system", "content": system_prompt}] + context_chat if system_prompt else context_chat

        curl_command = self.construct_curl_command(max_tokens, messages, stream_file)

        with open(os.devnull, 'w') as devnull:
            process = subprocess.Popen(curl_command, stdout=devnull, stderr=devnull)

        write_file(pid_stream_file, str(process.pid))

    def read_stream(self, stream_file, chat_file, pid_stream_file, stream_marker):
        with open(stream_file, "r", encoding="utf-8") as file:
            stream_string = file.read()

        if stream_marker:
            return json.dumps({
                "rerun": 0.1,
                "variables": {"streaming_now": True},
                "response": f"{assistant_signature()}...",
                "behaviour": {"response": "append"}
                })

        if len(stream_string.strip()) > 0:
            response_text, error_message, has_stopped = self.parse_stream_response(stream_string)
        else:
            response_text, error_message, has_stopped = "", "", False

        stalled = time.time() - file_modified(stream_file) > 5

        if stalled:
            if response_text:
                append_chat(chat_file, {"role": "assistant", "content": response_text})
            delete_file(stream_file)
            delete_file(pid_stream_file)
            return json.dumps({
                "response": f"{response_text} [Connection Stalled]",
                "footer": "You can ask ChatGPT to continue the answer",
                "behaviour": {"response": "replacelast", "scroll": "end"}
            })

        if not stream_string:
            return json.dumps({
                "rerun": 0.1,
                "variables": {"streaming_now": True}
            })

        if not has_stopped:
            return json.dumps({
                "rerun": 0.1,
                "variables": {"streaming_now": True},
                "response": assistant_signature() + response_text,
                "behaviour": {"response": "replacelast"}
            })

        append_chat(chat_file, {"role": "assistant", "content": response_text})
        delete_file(stream_file)
        delete_file(pid_stream_file)

        footer_text = ""
        if error_message:
            response_text = f"{response_text} [Error: {error_message}]"
            footer_text = f"[{error_message}]"

        return json.dumps({
            "response": assistant_signature() + response_text,
            "footer": footer_text,
            "behaviour": {"response": "replacelast", "scroll": "end"}
        })