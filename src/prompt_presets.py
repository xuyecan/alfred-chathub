#!/usr/bin/env python3

import sys

from helper import *

SEPARATORS = ("|", "｜")


def _truncate(text, limit):
    # 避免过长提示词影响列表可读性
    if not text:
        return ""
    single_line = " ".join(text.split())
    return single_line if len(single_line) <= limit else single_line[: max(0, limit - 1)] + "…"


def parse_presets(raw):
    presets = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        position = min((line.find(s) for s in SEPARATORS if s in line), default=-1)
        if position <= 0:
            continue
        name = line[:position].strip()
        prompt = line[position + 1:].strip().replace("\\n", "\n")
        if name and prompt:
            presets.append({"name": name, "prompt": prompt})
    return presets


def match_preset(presets, query):
    """名称从长到短匹配，这样名称本身含空格也不会把正文切错"""
    lowered = query.lower()
    for preset in sorted(presets, key=lambda p: -len(p["name"])):
        name = preset["name"].lower()
        if lowered == name:
            return preset, ""
        if lowered.startswith(name + " "):
            return preset, query[len(preset["name"]):].strip()
    return None, query


def preset_item(preset, question="", matched=False):
    preview = _truncate(preset["prompt"], 90)

    item = {
        "title": question or preset["name"],
        "subtitle": f"{preset['name']} · {preview}" if question else preview,
        "arg": question,
        "valid": True,
        "variables": {"preset_prompt": preset["prompt"]},
        "icon": {"path": "icon.png"}
    }

    if question:
        # 已经输入正文时不给 autocomplete，否则按 ⇥ 会把正文抹掉
        return item

    item["autocomplete"] = preset["name"]
    if matched:
        item["subtitle"] = f"↩ Open chat with this prompt applied · {preview}"
    return item


def run(argv):
    query = (argv[0] if argv else "").strip()
    presets = parse_presets(env_var("prompt_presets"))

    if not presets:
        return json.dumps({
            "items": [{
                "title": "No Prompt Presets Configured",
                "subtitle": "Configure workflow → Prompt Presets, one per line: name | prompt",
                "valid": False
            }]
        })

    matched, question = match_preset(presets, query)
    if matched:
        return json.dumps({"items": [preset_item(matched, question, matched=True)]})

    candidates = [p for p in presets if query.lower() in p["name"].lower()] if query else presets
    if not candidates:
        return json.dumps({
            "items": [{
                "title": f"No Preset Named “{query}”",
                "subtitle": "Configure workflow → Prompt Presets, one per line: name | prompt",
                "valid": False
            }]
        })

    return json.dumps({"items": [preset_item(p, "") for p in candidates]})


if __name__ == "__main__":
    print(run(sys.argv[1:]))
