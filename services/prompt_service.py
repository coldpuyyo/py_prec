import json

def load_prompt():
    with open("data/prompts.json", "r", encoding="utf-8") as f:
        return json.load(f)

def update_prompt(new_prompt):
    with open("data/prompts.json", "w", encoding="utf-8") as f:
        json.dump(new_prompt, f, ensure_ascii=False, indent=2)