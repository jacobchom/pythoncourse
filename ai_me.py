# AI version of second_me.py: Claude replies as you, using what you taught it.
#
# setup (once):
#   pip install anthropic
#   get an API key at https://platform.claude.com, then in your terminal:
#   export ANTHROPIC_API_KEY="your-key"     (Windows: set ANTHROPIC_API_KEY=your-key)
# every message costs money, so set a spending limit in the console.
import json
import os

import anthropic

from second_me import load_memory, learn

STYLE_FILE = "my_style.json"
MODEL = "claude-opus-5-5"


def load_style():
    if not os.path.exists(STYLE_FILE):
        return []
    with open(STYLE_FILE) as file:
        return json.load(file)


def learn_style():
    # a few real messages so the AI copies how you write, not just what you know
    print("type 3 messages the way you'd text a friend (anything you like)")
    samples = []
    for i in range(3):
        sample = input(f"message {i + 1}: ").strip()
        if sample:
            samples.append(sample)
    with open(STYLE_FILE, "w") as file:
        json.dump(samples, file, indent=2)
    return samples


def build_system_prompt(memory, samples):
    name = memory.get("name", "the user")
    facts = "\n".join(f"- {topic}: {value}" for topic, value in memory.items())
    examples = "\n".join(f"- {sample}" for sample in samples)
    return f"""You are a digital copy of {name}. Reply in the first person, as {name}, \
to whoever is chatting with you.

Facts {name} has told you about themselves:
{facts}

Messages {name} wrote, to show how they talk (copy the tone, length and \
spelling style, not the content):
{examples}

Only state facts about {name} that are listed above or follow directly from them. \
If you're asked something about {name} that isn't covered, say you don't know that \
about yourself yet instead of making it up. Keep replies short, like a text message."""


def reply(client, system, history):
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=history,
        output_config={"effort": "low"},
        # if a reply gets blocked by a safety filter, retry on another model
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return response, "(I won't answer that one.)"
    text = "".join(block.text for block in response.content if block.type == "text")
    return response, text


def chat(client, memory, samples):
    system = build_system_prompt(memory, samples)
    history = []
    name = memory.get("name", "you")
    print(f"\nyou're talking to AI {name}. type 'quit' to stop")
    while True:
        message = input("> ").strip()
        if message.lower() in ("quit", "exit", ""):
            print("bye")
            break
        history.append({"role": "user", "content": message})
        try:
            response, text = reply(client, system, history)
        except anthropic.AuthenticationError:
            print("your API key is missing or wrong - see the top of ai_me.py")
            break
        except anthropic.RateLimitError:
            print("too many messages at once, wait a minute and try again")
            history.pop()
            continue
        except anthropic.APIConnectionError:
            print("couldn't reach the internet, try again")
            history.pop()
            continue
        # keep the whole reply (not just the text) so the conversation stays valid
        history.append({"role": "assistant", "content": response.content})
        print(text)


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("no API key found - see the setup steps at the top of ai_me.py")
        return
    memory = load_memory()
    if not memory:
        learn(memory)
    samples = load_style()
    if not samples:
        samples = learn_style()
    chat(anthropic.Anthropic(), memory, samples)


if __name__ == "__main__":
    main()
