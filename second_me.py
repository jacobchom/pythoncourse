import json
import os
import shutil

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


# other ways people ask about the same topic
SYNONYMS = {
    "name": ["called", "who are you"],
    "age": ["old", "born"],
    "favourite food": ["eat", "food", "hungry", "meal"],
    "favourite subject": ["subject", "school", "lesson", "study"],
    "hobby": ["fun", "free time", "hobbies", "enjoy"],
    "goal": ["achieve", "want to be", "dream", "aim", "future"],
}


def has_words(question, phrase):
    # match whole words only, so "age" doesn't match "page"
    words = question.split()
    phrase_words = phrase.split()
    for i in range(len(words) - len(phrase_words) + 1):
        if words[i:i + len(phrase_words)] == phrase_words:
            return True
    return False


def find_topic(memory, question):
    question = "".join(c for c in question.lower() if c.isalnum() or c == " ")
    # longest topics first, so "favourite film" wins over a shorter match
    for topic in sorted(memory, key=len, reverse=True):
        if has_words(question, topic):
            return topic
    for topic, phrases in SYNONYMS.items():
        if topic in memory:
            for phrase in phrases:
                if has_words(question, phrase):
                    return topic
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


def clone(memory):
    # make another me: a copy of this program and everything it knows
    folder = "another_me"
    os.makedirs(folder, exist_ok=True)
    shutil.copy(__file__, os.path.join(folder, "second_me.py"))
    with open(os.path.join(folder, MEMORY_FILE), "w") as file:
        json.dump(memory, file, indent=2)
    return folder


def chat(memory):
    name = memory.get("name", "you")
    print(f"\nhi, I'm the second {name}. ask me about myself, "
          "type 'clone' to make another me, or 'quit'")
    while True:
        question = input("> ").strip()
        if question.lower() in ("quit", "exit", ""):
            print("bye")
            break
        if question.lower() == "clone":
            folder = clone(memory)
            print(f"done. another me is in {folder}/ - run it with: "
                  f"cd {folder} && python second_me.py")
            continue
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
