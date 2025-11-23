import json
import os
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from helper import (
    append_chat,
    assistant_signature,
    delete_file,
    env_var,
    file_modified,
    write_file,
)


class LLMService(ABC):
    def __init__(
        self, api_endpoint, api_key, model, http_proxy=None, socks5_proxy=None
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.model = model
        self.user_agent = "Alfred-Chathub"
        # 解析全局卡顿判定超时时间；限定允许值集合并设定安全缺省
        timeout_str = env_var("stall_timeout_sec") or "30"
        try:
            timeout_val = int(timeout_str)
        except Exception:
            timeout_val = 30
        self.stall_timeout_sec = timeout_val if timeout_val in {15, 30, 60, 120} else 30

        if http_proxy:
            self.proxy_option = ["-x", f"http://{http_proxy}"]
        elif socks5_proxy:
            self.proxy_option = ["--socks5-hostname", f"socks5://{socks5_proxy}"]
        else:
            self.proxy_option = []

    @abstractmethod
    def construct_curl_command(self, max_tokens, messages, stream_file) -> list:
        pass

    @abstractmethod
    def parse_stream_response(self, stream_string) -> Tuple[str, Optional[str], bool]:
        pass

    def remove_empty_assistant_messages(self, messages):
        i = 0
        while i < len(messages):
            if messages[i]["role"] == "assistant" and not messages[i]["content"]:
                if i > 0 and messages[i - 1]["role"] == "user":
                    # Remove both the empty assistant message and the preceding user message
                    del messages[i]
                    del messages[i - 1]
                    i -= 1
                else:
                    # If there's no preceding user message, just remove the assistant message
                    del messages[i]
            else:
                i += 1
        return messages

    def start_stream(
        self, max_tokens, system_prompt, context_chat, stream_file, pid_stream_file
    ):
        write_file(stream_file, "")

        while len(context_chat) > 0 and context_chat[0]["role"] == "assistant":
            context_chat.pop(0)

        messages = (
            [{"role": "system", "content": system_prompt}] + context_chat
            if system_prompt
            else context_chat
        )

        self.remove_empty_assistant_messages(messages)

        curl_command = self.construct_curl_command(max_tokens, messages, stream_file)

        with open(os.devnull, "w") as devnull:
            process = subprocess.Popen(curl_command, stdout=devnull, stderr=devnull)

        write_file(pid_stream_file, str(process.pid))

    def read_stream(self, stream_file, chat_file, pid_stream_file, stream_marker):
        with open(stream_file, "r", encoding="utf-8") as file:
            stream_string = file.read()

        if stream_marker:
            return json.dumps(
                {
                    "rerun": 0.1,
                    "variables": {"streaming_now": True},
                    "response": f"{assistant_signature()}...",
                    "behaviour": {"response": "append"},
                }
            )

        if len(stream_string.strip()) > 0:
            response_text, error_message, has_stopped = self.parse_stream_response(
                stream_string
            )
        else:
            response_text, error_message, has_stopped = "", "", False

        stalled = time.time() - file_modified(stream_file) > self.stall_timeout_sec

        if stalled:
            if response_text:
                append_chat(chat_file, {"role": "assistant", "content": response_text})
            delete_file(stream_file)
            delete_file(pid_stream_file)
            return json.dumps(
                {
                    "response": f"{response_text} [Connection Stalled]",
                    "footer": "You can ask the assistant to continue the answer",
                    "behaviour": {"response": "replacelast", "scroll": "end"},
                }
            )

        if not stream_string:
            return json.dumps({"rerun": 0.1, "variables": {"streaming_now": True}})

        if not has_stopped:
            return json.dumps(
                {
                    "rerun": 0.1,
                    "variables": {"streaming_now": True},
                    "response": assistant_signature() + response_text,
                    "behaviour": {"response": "replacelast"},
                }
            )

        append_chat(
            chat_file,
            {"role": "assistant", "content": response_text or error_message or ""},
        )
        delete_file(stream_file)
        delete_file(pid_stream_file)

        footer_text = ""
        if error_message:
            response_text = f"{response_text} [Error: {error_message}]"
            footer_text = f"[{error_message}]"

        return json.dumps(
            {
                "response": assistant_signature() + response_text,
                "footer": footer_text,
                "behaviour": {"response": "replacelast", "scroll": "end"},
            }
        )
