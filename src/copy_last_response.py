#!/usr/bin/env python3

from llm_service import *

def run():
    chat_file = f"{env_var('alfred_workflow_data')}/chat.json"
    messages = read_chat(chat_file)
    assistant_message = next((message for message in reversed(messages) if message["role"] == "assistant"), None)
    message = assistant_message["content"] if assistant_message else None
    if not message:
        return ""
    return message[len("#### Assistant\n"):]

if __name__ == "__main__":
    print(run())