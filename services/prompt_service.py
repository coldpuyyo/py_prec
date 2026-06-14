from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRAPGENARATOR_PROMPTS_PATH = ROOT_DIR / "data" / "scrapgenarator_prompts.json"
KEYWORDGENARATOR_PROMPTS_PATH = ROOT_DIR / "data" / "keywordgenarator_prompts.json"
BLOGSCRAPGENARATOR_PROMPTS_PATH = ROOT_DIR / "data" / "blogscrapgenarator_prompts.json"
TITLEGENARATOR_PROMPT_PATH = ROOT_DIR / "data" / "titlegenarator_prompt.json"

DEFAULT_PROMPT = {"blog_prompt": ""}
DEFAULT_TITLE_PROMPT = {"title_prompt": ""}


def load_scrapgenarator_prompt() -> dict:
    if not SCRAPGENARATOR_PROMPTS_PATH.exists():
        SCRAPGENARATOR_PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCRAPGENARATOR_PROMPTS_PATH.write_text(
            json.dumps(DEFAULT_PROMPT, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dict(DEFAULT_PROMPT)

    raw = SCRAPGENARATOR_PROMPTS_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return dict(DEFAULT_PROMPT)

    data = json.loads(raw)
    if not isinstance(data, dict):
        return dict(DEFAULT_PROMPT)

    data.setdefault("blog_prompt", "")
    return data


def update_scrapgenarator_prompt(new_prompt: dict) -> None:
    payload = dict(DEFAULT_PROMPT)
    if isinstance(new_prompt, dict):
        payload["blog_prompt"] = str(new_prompt.get("blog_prompt", "")).strip()

    SCRAPGENARATOR_PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCRAPGENARATOR_PROMPTS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    
def load_keywordgenarator_prompt() -> dict:
    if not KEYWORDGENARATOR_PROMPTS_PATH.exists():
        KEYWORDGENARATOR_PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        KEYWORDGENARATOR_PROMPTS_PATH.write_text(
            json.dumps(DEFAULT_PROMPT, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dict(DEFAULT_PROMPT)
    
    raw = KEYWORDGENARATOR_PROMPTS_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return dict(DEFAULT_PROMPT)

    data = json.loads(raw)
    if not isinstance(data, dict):
        return dict(DEFAULT_PROMPT)

    data.setdefault("blog_prompt", "")
    return data

def update_keywordgenarator_prompt(new_prompt: dict) -> None:
    payload = dict(DEFAULT_PROMPT)
    if isinstance(new_prompt, dict):
        payload["blog_prompt"] = str(new_prompt.get("blog_prompt", "")).strip()

    KEYWORDGENARATOR_PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYWORDGENARATOR_PROMPTS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_blogscrapgenarator_prompt() -> dict:
    if not BLOGSCRAPGENARATOR_PROMPTS_PATH.exists():
        BLOGSCRAPGENARATOR_PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        BLOGSCRAPGENARATOR_PROMPTS_PATH.write_text(
            json.dumps(DEFAULT_PROMPT, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dict(DEFAULT_PROMPT)

    raw = BLOGSCRAPGENARATOR_PROMPTS_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return dict(DEFAULT_PROMPT)

    data = json.loads(raw)
    if not isinstance(data, dict):
        return dict(DEFAULT_PROMPT)

    data.setdefault("blog_prompt", "")
    return data


def update_blogscrapgenarator_prompt(new_prompt: dict) -> None:
    payload = dict(DEFAULT_PROMPT)
    if isinstance(new_prompt, dict):
        payload["blog_prompt"] = str(new_prompt.get("blog_prompt", "")).strip()

    BLOGSCRAPGENARATOR_PROMPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BLOGSCRAPGENARATOR_PROMPTS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_titlegenarator_prompt() -> dict:
    if not TITLEGENARATOR_PROMPT_PATH.exists():
        TITLEGENARATOR_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        TITLEGENARATOR_PROMPT_PATH.write_text(
            json.dumps(DEFAULT_TITLE_PROMPT, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dict(DEFAULT_TITLE_PROMPT)

    raw = TITLEGENARATOR_PROMPT_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return dict(DEFAULT_TITLE_PROMPT)

    data = json.loads(raw)
    if not isinstance(data, dict):
        return dict(DEFAULT_TITLE_PROMPT)

    data.setdefault("title_prompt", "")
    return data


def update_titlegenarator_prompt(new_prompt: dict) -> None:
    payload = dict(DEFAULT_TITLE_PROMPT)
    if isinstance(new_prompt, dict):
        payload["title_prompt"] = str(new_prompt.get("title_prompt", "")).strip()

    TITLEGENARATOR_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TITLEGENARATOR_PROMPT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
