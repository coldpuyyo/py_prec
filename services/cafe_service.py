import json

def load_cafes():
    with open("data/cafes.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_cafes_by_category(category: str):
    cafes = load_cafes()

    return [
        cafe for cafe in cafes
        if cafe.get("category") == category
    ]