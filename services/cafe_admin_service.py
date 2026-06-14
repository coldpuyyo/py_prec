from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from services.naver_profile_registry_service import is_active_profile_for_role

ROOT_DIR = Path(__file__).resolve().parents[1]
CAFES_PATH = ROOT_DIR / "data" / "cafes.json"
CATEGORIES_PATH = ROOT_DIR / "data" / "categories.json"

ALLOWED_FILTER_TYPES = {"keyword", "exclude"}
DEFAULT_EXCLUDE = ["공지", "필독"]


def _read_json(path: Path, default):
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return default
    return json.loads(raw)


def _write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean(value) -> str:
    return str(value or "").strip()


def sync_categories_from_cafes(cafes: list[dict] | None = None) -> list[str]:
    if cafes is None:
        cafes = _read_json(CAFES_PATH, [])

    categories: list[str] = []
    for cafe in cafes:
        cat = _clean(cafe.get("category"))
        if cat and cat not in categories:
            categories.append(cat)

    current = _read_json(CATEGORIES_PATH, [])
    if current != categories:
        _write_json(CATEGORIES_PATH, categories)

    return categories


def list_cafes() -> list[dict]:
    cafes = _read_json(CAFES_PATH, [])
    changed = False

    for cafe in cafes:
        if not _clean(cafe.get("id")):
            cafe["id"] = uuid4().hex[:12]
            changed = True
        if "keyword" not in cafe:
            cafe["keyword"] = ""
            changed = True
        if not _clean(cafe.get("filter_type")):
            cafe["filter_type"] = "keyword"
            changed = True

        # 추가: 멤버/계정 메타데이터 기본값
        if "member_required" not in cafe:
            cafe["member_required"] = False
            changed = True

        legacy_key = _clean(cafe.get("naver_account_key"))
        if "scraper_profile_key" not in cafe and legacy_key:
            cafe["scraper_profile_key"] = legacy_key
            changed = True
        if "scraper_profile_key" not in cafe:
            cafe["scraper_profile_key"] = ""
            changed = True

        if "naver_account_key" not in cafe:
            cafe["naver_account_key"] = ""
            changed = True

    if changed:
        _write_json(CAFES_PATH, cafes)

    sync_categories_from_cafes(cafes)
    return cafes


def _validate_payload(payload: dict) -> tuple[list[str], dict]:
    category = _clean(payload.get("category"))
    name = _clean(payload.get("name"))
    url = _clean(payload.get("url"))
    filter_type = _clean(payload.get("filter_type"))
    keyword = _clean(payload.get("keyword"))

    # 추가
    member_required = bool(payload.get("member_required"))
    scraper_profile_key = _clean(payload.get("scraper_profile_key") or payload.get("naver_account_key"))

    errors: list[str] = []

    if not category:
        errors.append("카테고리는 필수입니다.")
    if not name:
        errors.append("카페명은 필수입니다.")
    if not url:
        errors.append("URL은 필수입니다.")
    if not (url.startswith("http://") or url.startswith("https://")):
        errors.append("URL 형식이 올바르지 않습니다.")
    if filter_type not in ALLOWED_FILTER_TYPES:
        errors.append("필터 타입은 키워드 또는 공지, 필독 제외만 허용됩니다.")
    if filter_type == "keyword" and not keyword:
        errors.append("필터 타입이 키워드이면 키워드는 필수입니다.")
    if member_required and not scraper_profile_key:
        errors.append("멤버 가입 필요가 true이면 스크랩 계정 키는 필수입니다.")
    if member_required and scraper_profile_key and not is_active_profile_for_role(scraper_profile_key, "scraper"):
        errors.append("유효한 scraper 프로필 키가 아닙니다.")

    cleaned = {
        "category": category,
        "name": name,
        "url": url,
        "filter_type": filter_type,
        "keyword": keyword if filter_type == "keyword" else "",
        # 추가
        "member_required": member_required,
        "scraper_profile_key": scraper_profile_key,
        "naver_account_key": scraper_profile_key,
    }

    return errors, cleaned

def create_cafe(payload: dict) -> dict:
    errors, cleaned = _validate_payload(payload)
    if errors:
        return {"ok": False, "message": " / ".join(errors)}

    cafes = list_cafes()

    if any(
        _clean(x.get("category")) == cleaned["category"] and _clean(x.get("url")) == cleaned["url"]
        for x in cafes
    ):
        return {"ok": False, "message": "같은 category + url 항목이 이미 존재합니다."}

    item = {"id": uuid4().hex[:12], **cleaned}
    if item["filter_type"] == "exclude":
        item["exclude"] = DEFAULT_EXCLUDE.copy()

    cafes.append(item)
    _write_json(CAFES_PATH, cafes)
    sync_categories_from_cafes(cafes)

    return {"ok": True, "item": item}


def update_cafe(cafe_id: str, payload: dict) -> dict:
    cafe_id = _clean(cafe_id)
    if not cafe_id:
        return {"ok": False, "message": "cafe_id가 비어 있습니다."}

    errors, cleaned = _validate_payload(payload)
    if errors:
        return {"ok": False, "message": " / ".join(errors)}

    cafes = list_cafes()
    target = next((x for x in cafes if _clean(x.get("id")) == cafe_id), None)
    if not target:
        return {"ok": False, "message": "해당 cafe_id를 찾을 수 없습니다."}

    target.update(cleaned)

    if target["filter_type"] == "keyword":
        target.pop("exclude", None)
    else:
        target.setdefault("exclude", DEFAULT_EXCLUDE.copy())

    _write_json(CAFES_PATH, cafes)
    sync_categories_from_cafes(cafes)

    return {"ok": True, "item": target}


def delete_cafe(cafe_id: str) -> dict:
    cafe_id = _clean(cafe_id)
    cafes = list_cafes()

    new_cafes = [x for x in cafes if _clean(x.get("id")) != cafe_id]
    if len(new_cafes) == len(cafes):
        return {"ok": False, "message": "해당 cafe_id를 찾을 수 없습니다."}

    _write_json(CAFES_PATH, new_cafes)
    sync_categories_from_cafes(new_cafes)

    return {"ok": True}
