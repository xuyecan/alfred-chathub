#!/usr/bin/env python3

import json
import os

from helper import (
    dir_contents,
    env_var,
    file_exists,
    no_archives,
    read_chat,
    trash_chat,
)


def _truncate(text, limit):
    # 避免过长句子影响列表可读性
    if not text:
        return ""
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def run():
    archive_dir = os.path.join(env_var("alfred_workflow_data"), "archive")
    if not os.path.exists(archive_dir):
        return no_archives()

    items = []
    chat_files = dir_contents(archive_dir)

    ongoing_chat_file = os.path.join(env_var("alfred_workflow_data"), "chat.json")
    if file_exists(ongoing_chat_file):
        chat_files.append(ongoing_chat_file)

    for file in reversed(chat_files):
        if file.endswith(".json"):
            chat_contents = read_chat(file)
            first_question = next(
                (item["content"] for item in chat_contents if item["role"] == "user"),
                None,
            )
            last_question = next(
                (
                    item["content"]
                    for item in reversed(chat_contents)
                    if item["role"] == "user"
                ),
                None,
            )

            # Delete invalid chats
            if not first_question:
                trash_chat(file)
                continue

            uid = os.path.basename(file)
            title = _truncate(first_question, 80)
            subtitle = _truncate(last_question or "", 120)
            items.append(
                {
                    "uid": uid,
                    "title": title,
                    "subtitle": subtitle,
                    "match": f"{first_question} {last_question}",
                    "arg": file,
                    "valid": True,
                    "text": {
                        "copy": f"{first_question} — {last_question or ''}",
                        "largetype": title,
                    },
                }
            )

    if not items:
        return json.dumps(
            {
                "items": [
                    {
                        "title": "No Chat Histories Found",
                        "subtitle": "Start a new chat, then save",
                        "arg": "",
                        "valid": False,
                    }
                ]
            }
        )

    return json.dumps({"items": items})


if __name__ == "__main__":
    print(run())
