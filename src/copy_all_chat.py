#!/usr/bin/env python3

from helper import env_var, markdown_chat, read_chat


def run():
    chat_file = f"{env_var('alfred_workflow_data')}/chat.json"
    return markdown_chat(read_chat(chat_file), False)


if __name__ == "__main__":
    print(run())
