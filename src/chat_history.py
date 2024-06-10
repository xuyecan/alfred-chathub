#!/usr/bin/env python3

from helper import *

def run():
    archive_dir = os.path.join(env_var("alfred_workflow_data"), "archive")
    if not os.path.exists(archive_dir):
        return no_archives()

    sf_items = []
    chat_files = dir_contents(archive_dir)

    ongoing_chat_file = os.path.join(env_var("alfred_workflow_data"), "chat.json")
    if file_exists(ongoing_chat_file):
        chat_files.append(ongoing_chat_file)

    for file in reversed(chat_files):
        if file.endswith(".json"):
            chat_contents = read_chat(file)
            first_question = next((item["content"] for item in chat_contents if item["role"] == "user"), None)
            last_question = next((item["content"] for item in reversed(chat_contents) if item["role"] == "user"), None)

            # Delete invalid chats
            if not first_question:
                trash_chat(file)
                continue

            sf_items.append({
                "type": "file",
                "title": first_question,
                "subtitle": last_question,
                "match": f"{first_question} {last_question}",
                "arg": file
            })

    if not sf_items:
        return no_archives()

    return json.dumps({ "items": sf_items })

if __name__ == "__main__":
    print(run())