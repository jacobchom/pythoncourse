import json
import os

MEMORY_FILE = "me.json"

STARTER_QUESTIONS = {
    "name": "what is your name: ",
    "age": "how old are you: ",
    "favourite food": "what is your favourite food: ",
    "favourite subject": "what is your favourite subject: ",
    "hobby": "what do you do for fun: ",
    "goal": "what is one thing you want to achieve: ",
}


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE) as file:
        return json.load(file)


def save_memory(memory):
    with open(MEMORY_FILE, "w") as file:
        json.dump(memory, file, indent=2)


def learn(memory):
    print("teach me who you are (press enter to skip a question)")
    for topic, question in STARTER_QUESTIONS.items():
        answer = input(question).strip()
        if answer:
            memory[topic] = answer
    save_memory(memory)


def find_topic(memory, question):
    question = question.lower()
    for topic in memory:
        if topic in question:
            return topic
    # "how old" is how people ask about age, even without the word "age"
    if "old" in question and "age" in memory:
        return "age"
    return None


def answer(memory, question):
    topic = find_topic(memory, question)
    if topic == "name":
        return f"I'm {memory['name']}."
    if topic == "age":
        return f"I'm {memory['age']}."
    if topic:
        return f"My {topic} is {memory[topic]}."
    return None


def chat(memory):
    name = memory.get("name", "you")
    print(f"\nhi, I'm the second {name}. ask me about myself, or type 'quit'")
    while True:
        question = input("> ").strip()
        if question.lower() in ("quit", "exit", ""):
            print("bye")
            break
        reply = answer(memory, question)
        if reply:
            print(reply)
            continue
        # unknown topic: ask the real me to teach the second me
        print("I don't know that about myself yet.")
        topic = input("what is it about? (e.g. 'favourite film'): ").strip().lower()
        if topic:
            memory[topic] = input(f"what is your {topic}: ").strip()
            save_memory(memory)
            print("got it, now I know that too.")


def main():
    memory = load_memory()
    if not memory:
        learn(memory)
    chat(memory)


if __name__ == "__main__":
    main()
