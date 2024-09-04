# Chat-bot

## Overview

**Chat-bot** is a Discord bot that simulates a conversation with a virtual character using natural language processing. The bot is designed to create interactive and engaging conversations within Discord channels, allowing users to interact with a virtual character with a pre-defined personality and traits. Additionally, the bot can convert speech to text, respond to text prompts, and generate audio responses.

## Features

- **Interactive Chat:** The bot simulates a conversation with a character using a pre-defined role and personality in a virtual setting.
- **Text-to-Speech (TTS):** Generates audio responses based on the text output.
- **Audio Playback in Voice Channels:** The bot can join a voice channel and play the generated audio.
- **Customizable Prompts:** You can modify the prompt used by the bot to customize the virtual character's personality and responses.
- **Supports Multiple Discord Commands:** Commands to enable or disable auto-reply, join or leave voice channels, and respond to user input.

## Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/your-username/Chat-bot.git --recursive
    cd Chat-bot
    ```

2. Configure the Bot:

    Create a config.py file in the root directory of the project and add your Discord bot token:
    ```python
    TOKEN = "YOUR_DISCORD_BOT_TOKEN"
    ```

3. Run the Bot:

Start the bot by running the following command:
    ```bash
    python main.py
    ```

## Commands

* **!enable**
Enables auto-reply in the current channel.

* **!disable**
Disables auto-reply in the current channel.

* **!chat <message>**
Sends a message to the bot, and it replies based on the defined personality prompt.

* **!join**
Makes the bot join the voice channel that the user is currently in.

* **!leave**
Makes the bot leave the voice channel.

## Customizing the Bot
You can customize the bot's behavior by editing the LLM_PROMPT, LLM_LAST_10_MSG, and LLM_REPLY_PROMPT variables in the bot.py file. These variables define the virtual character's personality, behavior, and how it responds to different prompts.

### Example of Changing the Prompt
```python
LLM_PROMPT = """Your new custom prompt goes here..."""
LLM_REPLY_PROMPT = """Follow this format to respond..."""
````

Modify these prompts to adjust the character's personality, traits, and response style to fit your requirements.

## Usage
1. Start the Bot:

    * Run the bot using the provided commands. Ensure your Discord bot token is correctly set in the config.py file.

2. Join a Voice Channel:

    * Use the !join command to make the bot join your current voice channel. The bot will then start playing any generated audio responses.

3. Send Messages:

    * Send messages or commands directly in the text channel to interact with the bot. If auto-reply is enabled, the bot will automatically respond to messages.

4. Leave a Voice Channel:

    * Use the !leave command to disconnect the bot from the voice channel.

## Issue: GPU Out of Memory During High Traffic
### Description
When the bot is handling multiple users or when there is a high density of messages, it occasionally causes the GPU to run out of memory. This issue results in the failure of both voice generation and text response functionalities.

### Steps to Reproduce
1. Have multiple users interact with the bot simultaneously in different channels.
2. Send a rapid series of messages in a short period to the bot.
3. Observe if the GPU memory usage increases significantly, leading to an out-of-memory error.

### Expected Behavior
The bot should handle multiple users and dense message traffic without causing the GPU to run out of memory, ensuring continuous voice and text responses.

### Actual Behavior
Under high traffic or with multiple users, the GPU runs out of memory, causing the bot to fail in generating audio or responding to text messages.

### Possible Solutions
* Implement a queuing system to limit the number of simultaneous requests processed by the GPU.
* Optimize the memory usage of the model to prevent GPU overload.
* Use a fallback mechanism to handle out-of-memory errors gracefully without crashing the bot.
### Additional Context
This issue is particularly prominent when running the bot in servers with multiple active users and high message rates.

## Notes
* Ensure your Discord bot has all the necessary permissions to perform its tasks, including reading and sending messages and connecting to voice channels.
* You can adjust the bot's personality and response style by editing the prompt variables.