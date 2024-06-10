#!/usr/bin/env python3

import os
from datetime import datetime
from helper import *

def pad_date(number):
    return str(number).zfill(2)

def run():
    uid = os.urandom(16).hex()[:8]  # Generates a unique identifier
    current_date = datetime.now()
    current_year = current_date.year
    current_month = pad_date(current_date.month)
    current_day = pad_date(current_date.day)
    current_hour = pad_date(current_date.hour)
    current_minute = pad_date(current_date.minute)
    current_second = pad_date(current_date.second)

    current_chat = f"{env_var('alfred_workflow_data')}/chat.json"
    replacement_chat = env_var('replace_with_chat')
    archive_dir = f"{env_var('alfred_workflow_data')}/archive"
    archived_chat = f"{archive_dir}/{current_year}.{current_month}.{current_day}.{current_hour}.{current_minute}.{current_second}-{uid}.json"

    make_dir(archive_dir)
    mv(current_chat, archived_chat)

    if replacement_chat:
        mv(replacement_chat, current_chat)
    else:
        write_file(current_chat, "[]")

if __name__ == "__main__":
    run()