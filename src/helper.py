import os
import json
import shutil
from pathlib import Path

def env_var(var_name):
    return os.environ.get(var_name)

def user_signature():
    return "**You:**\n\n"

def assistant_signature():
    return "**Assistant:**\n\n"

def make_dir(path):
    os.makedirs(path, exist_ok=True)

def dir_contents(path):
    return sorted([str(p) for p in Path(path).iterdir() if p.is_file() and not p.name.startswith('.')])

def mv(init_path, target_path):
    shutil.move(init_path, target_path)

def file_exists(path):
    return os.path.exists(path)

def file_modified(path):
    return os.path.getmtime(path)

def delete_file(path):
    if file_exists(path):
        os.remove(path)

def write_file(path, text):
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)

def read_chat(path):
    if not file_exists(path):
        return []
    with open(path, "r", encoding="utf-8") as file:
        chat_string = file.read()
    return json.loads(chat_string)

def trash_chat(path):
    shutil.move(path, os.path.expanduser("~/.Trash"))

def append_chat(path, message):
    ongoing_chat = read_chat(path) + [message]
    chat_string = json.dumps(ongoing_chat)
    write_file(path, chat_string)

def markdown_chat(messages, ignore_last_interrupted=True):
    result = ""
    for index, current in enumerate(messages):
        if current["role"] == "assistant":
            result += assistant_signature() + current["content"] + "\n\n"
        elif current["role"] == "user":
            user_message = user_signature() + "\n".join(f"{line}" for line in current["content"].split("\n"))
            user_twice = index + 1 < len(messages) and messages[index + 1]["role"] == "user"
            last_message = index == len(messages) - 1
            if user_twice or (last_message and not ignore_last_interrupted):
                result += f"{user_message}\n\n[Answer Interrupted]\n\n"
            else:
                result += f"{user_message}\n\n"
        result += "---\n"
    return result

def no_archives():
    return json.dumps({
        "items": [{
            "title": "No Chat Histories Found",
            "subtitle": "Archives are created when starting new conversations",
            "valid": False
        }]
    })