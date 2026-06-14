from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CAFES_PATH = ROOT_DIR / "data" / "cafes.json"


def load_cafes() -> list[dict]:
    if not CAFES_PATH.exists():
        return []

    raw = CAFES_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return []

    cafes = json.loads(raw)
    if not isinstance(cafes, list):
        return []

    # 구버전 키 방어
    for cafe in cafes:
        if not isinstance(cafe, dict):
            continue
        cafe.setdefault("member_required", False)
        cafe.setdefault("naver_account_key", "")
        cafe.setdefault("scraper_profile_key", cafe.get("naver_account_key", ""))
        cafe.setdefault("keyword", "")

    return cafes


def get_cafes_by_category(category: str) -> list[dict]:
    cafes = load_cafes()
    return [cafe for cafe in cafes if cafe.get("category") == category]