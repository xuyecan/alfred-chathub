# <img src='icon.png' width='45' align='center' alt='icon'> Alfred-Chathub

A chat tool that integrates multiple popular large language model (LLM) services, including OpenAI, Anthropic, Gemini, DeepSeek, etc. Currently supports:
- [x] OpenAI
- [x] Anthropic
- [x] Gemini
- [x] Qwen
- [x] Deepseek

With the release of Alfred version 5.5, Alfred officially provided the [ChatGPT Workflow](https://github.com/alfredapp/openai-workflow), but it only supports OpenAI integration. When I installed and used it, my OpenAI API Key happened to be banned. Moreover, the ChatGPT Workflow is mainly based on JXA (JavaScript for Automation), which is difficult to extend. Therefore, I rewrote it in Python and extended support for other LLM services such as Anthropic, Gemini, and Deepseek. Now, introducing support for a new LLM service is very easy.

## Requirements

- Alfred 5 (Powerpack required). This workflow relies on Alfred 5's User Configuration panel and automation APIs.
- Python 3 available on your system. Verify with:
  - `/usr/bin/env python3 -c "import sys; print(sys.executable)"`

## Prerequisites

1. Choose an LLM provider, register on its website, and obtain an API Key.
2. Ensure your Python 3 path resolves correctly as above.

Here is how to get those api-keys:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys
- Gemini: https://ai.google.dev/gemini-api/docs/api-key
- (Qwen)通义千问: https://help.aliyun.com/zh/dashscope/developer-reference/activate-dashscope-and-create-an-api-key
- Deepseek: https://platform.deepseek.com/api_keys

## Usage

1. Install the workflow. Typically, you just need to download the latest version from the release page and click to install it.
2. Perform basic configuration. Select a provider and set its API Key and Model. If necessary, set a proxy.

<img src="assets/main_config.png" alt="Main Config" width="500" style="margin-left: 25px">

3. Make sure the endpoint is correct.

<img src="assets/endpoint_config.png" alt="Endpoint Config" width="500" style="margin-left: 25px">

4. Switch provider quickly with `chp`.

   - Invoke Alfred and type `chp`, then pick a provider from the list.
   - Your selection is immediately written back to Alfred's Configure panel (User Configuration) and becomes the active provider for chats.
   - The current provider is also highlighted in the `chp` list for quick confirmation.

5. Enjoy.
> Tip: Enhance your user experience by adding hotkey triggers. After installation, the workflow's hotkey triggers are initially unset. We recommend using Ctrl + Shift + Z to open chat history and Ctrl + Shift + X to start a new chat, but feel free to customize these to your liking.

<img src="assets/hotkey_setting.png" alt="Hotkey Setting" width="500" style="margin-left: 25px">

## Showcase
<p><img src="assets/ask_chathub.png" alt="Ask Chathub" width="500"></p>
<p><img src="assets/chat.png" alt="Chat" width="500"></p>
<p><img src="assets/history.png" alt="Chat History" width="500"></p>
