from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path

from PIL import Image, ImageEnhance

ROOT_DIR = Path(__file__).resolve().parents[1]
TOP_IMAGE_POOL_DIR = ROOT_DIR / "data" / "publish_image_pool" / "top"
MIDDLE_IMAGE_POOL_DIR = ROOT_DIR / "data" / "publish_image_pool" / "middle"
BOTTOM_IMAGE_POOL_DIR = ROOT_DIR / "data" / "publish_image_pool" / "bottom"
HYPER_IMAGE_POOL_DIR = ROOT_DIR / "data" / "publish_image_pool" / "hyper"
TOP_IMAGE_VARIANT_DIR = ROOT_DIR / "output" / "publish_image_variants" / "top"
MIDDLE_IMAGE_VARIANT_DIR = ROOT_DIR / "output" / "publish_image_variants" / "middle"
BOTTOM_IMAGE_VARIANT_DIR = ROOT_DIR / "output" / "publish_image_variants" / "bottom"
HYPER_IMAGE_VARIANT_DIR = ROOT_DIR / "output" / "publish_image_variants" / "hyper"
USED_TOP_SOURCES_PATH = TOP_IMAGE_VARIANT_DIR / "used_sources.json"
USED_MIDDLE_SOURCES_PATH = MIDDLE_IMAGE_VARIANT_DIR / "used_sources.json"
USED_BOTTOM_SOURCES_PATH = BOTTOM_IMAGE_VARIANT_DIR / "used_sources.json"
USED_HYPER_SOURCES_PATH = HYPER_IMAGE_VARIANT_DIR / "used_sources.json"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _clamp(v: int, low: int = 0, high: int = 255) -> int:
    return max(low, min(high, v))


def ensure_top_image_pool_dir() -> Path:
    TOP_IMAGE_POOL_DIR.mkdir(parents=True, exist_ok=True)
    TOP_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    return TOP_IMAGE_POOL_DIR

def ensure_middle_image_pool_dir() -> Path:
    MIDDLE_IMAGE_POOL_DIR.mkdir(parents=True, exist_ok=True)
    MIDDLE_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    return MIDDLE_IMAGE_POOL_DIR

def ensure_bottom_image_pool_dir() -> Path:
    BOTTOM_IMAGE_POOL_DIR.mkdir(parents=True, exist_ok=True)
    BOTTOM_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    return BOTTOM_IMAGE_POOL_DIR

def ensure_hyper_image_pool_dir() -> Path:
    HYPER_IMAGE_POOL_DIR.mkdir(parents=True, exist_ok=True)
    HYPER_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    return HYPER_IMAGE_POOL_DIR

def list_pool_top_images() -> list[Path]:
    ensure_top_image_pool_dir()
    items = [
        path
        for path in TOP_IMAGE_POOL_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
    ]
    return sorted(items)

def list_pool_middle_images() -> list[Path]:
    ensure_middle_image_pool_dir()
    items = [
        path
        for path in MIDDLE_IMAGE_POOL_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
    ]
    return sorted(items)

def list_pool_bottom_images() -> list[Path]:
    ensure_bottom_image_pool_dir()
    items = [
        path
        for path in BOTTOM_IMAGE_POOL_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
    ]
    return sorted(items)

def list_pool_hyper_images() -> list[Path]:
    ensure_hyper_image_pool_dir()
    items = [
        path
        for path in HYPER_IMAGE_POOL_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
    ]
    return sorted(items)


def _read_used_top_sources() -> list[str]:
    if not USED_TOP_SOURCES_PATH.exists():
        return []
    try:
        raw = USED_TOP_SOURCES_PATH.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [str(x) for x in data if str(x).strip()]
    except Exception:
        return []
    
def _read_used_middle_sources() -> list[str]:
    if not USED_MIDDLE_SOURCES_PATH.exists():
        return []
    try:
        raw = USED_MIDDLE_SOURCES_PATH.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [str(x) for x in data if str(x).strip()]
    except Exception:
        return []


def _read_used_bottom_sources() -> list[str]:
    if not USED_BOTTOM_SOURCES_PATH.exists():
        return []
    try:
        raw = USED_BOTTOM_SOURCES_PATH.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [str(x) for x in data if str(x).strip()]
    except Exception:
        return []


def _read_used_hyper_sources() -> list[str]:
    if not USED_HYPER_SOURCES_PATH.exists():
        return []
    try:
        raw = USED_HYPER_SOURCES_PATH.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [str(x) for x in data if str(x).strip()]
    except Exception:
        return []


def _write_used_top_sources(items: list[str]) -> None:
    USED_TOP_SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    USED_TOP_SOURCES_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    
def _write_used_middle_sources(items: list[str]) -> None:
    USED_MIDDLE_SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    USED_MIDDLE_SOURCES_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    
def _write_used_bottom_sources(items: list[str]) -> None:
    USED_BOTTOM_SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    USED_BOTTOM_SOURCES_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def _write_used_hyper_sources(items: list[str]) -> None:
    USED_HYPER_SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    USED_HYPER_SOURCES_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _pick_source_top_image(images: list[Path]) -> Path:
    used = set(_read_used_top_sources())
    unused = [path for path in images if path.name not in used]

    if not unused:
        used = set()
        unused = list(images)

    source = random.choice(unused)
    used.add(source.name)
    _write_used_top_sources(sorted(used))
    return source

def _pick_source_middle_image(images: list[Path]) -> Path:
    used = set(_read_used_middle_sources())
    unused = [path for path in images if path.name not in used]

    if not unused:
        used = set()
        unused = list(images)

    source = random.choice(unused)
    used.add(source.name)
    _write_used_middle_sources(sorted(used))
    return source

def _pick_source_bottom_image(images: list[Path]) -> Path:
    used = set(_read_used_bottom_sources())
    unused = [path for path in images if path.name not in used]

    if not unused:
        used = set()
        unused = list(images)

    source = random.choice(unused)
    used.add(source.name)
    _write_used_bottom_sources(sorted(used))
    return source

def _pick_source_hyper_image(images: list[Path]) -> Path:
    used = set(_read_used_hyper_sources())
    unused = [path for path in images if path.name not in used]

    if not unused:
        used = set()
        unused = list(images)

    source = random.choice(unused)
    used.add(source.name)
    _write_used_hyper_sources(sorted(used))
    return source

def _mutate_pixels_lightly(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    width, height = rgb.size
    px = rgb.load()

    points = max(120, min((width * height) // 2200, 3600))
    for _ in range(points):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        r, g, b = px[x, y]
        px[x, y] = (
            _clamp(r + random.randint(-3, 3)),
            _clamp(g + random.randint(-3, 3)),
            _clamp(b + random.randint(-3, 3)),
        )
    return rgb


def build_random_top_image_variant() -> dict:
    images = list_pool_top_images()
    if not images:
        return {
            "ok": False,
            "message": f"이미지 풀 폴더에 이미지가 없습니다: {TOP_IMAGE_POOL_DIR}",
            "image_path": "",
        }

    src = _pick_source_top_image(images)
    TOP_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as img:
        img = img.convert("RGB")
        width, height = img.size

        # Resize slightly.
        ratio = random.uniform(0.97, 1.03)
        new_w = max(120, int(width * ratio))
        new_h = max(120, int(height * ratio))
        if new_w != width or new_h != height:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Apply subtle visual changes.
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Color(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Sharpness(img).enhance(random.uniform(0.99, 1.03))
        img = _mutate_pixels_lightly(img)

        out_name = f"{src.stem}_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
        out_path = TOP_IMAGE_VARIANT_DIR / out_name
        img.save(
            out_path,
            format="JPEG",
            quality=random.randint(88, 94),
            optimize=True,
            progressive=True,
        )

    return {
        "ok": True,
        "message": "ok",
        "image_path": str(out_path),
        "source_path": str(src),
        "source_name": src.name,
    }

def build_random_middle_image_variant() -> dict:
    images = list_pool_middle_images()
    if not images:
        return {
            "ok": False,
            "message": f"이미지 풀 폴더에 이미지가 없습니다: {MIDDLE_IMAGE_POOL_DIR}",
            "image_path": "",
        }

    src = _pick_source_middle_image(images)
    MIDDLE_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as img:
        img = img.convert("RGB")
        width, height = img.size

        # Resize slightly.
        ratio = random.uniform(0.97, 1.03)
        new_w = max(120, int(width * ratio))
        new_h = max(120, int(height * ratio))
        if new_w != width or new_h != height:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Apply subtle visual changes.
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Color(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Sharpness(img).enhance(random.uniform(0.99, 1.03))
        img = _mutate_pixels_lightly(img)

        out_name = f"{src.stem}_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
        out_path = MIDDLE_IMAGE_VARIANT_DIR / out_name
        img.save(
            out_path,
            format="JPEG",
            quality=random.randint(88, 94),
            optimize=True,
            progressive=True,
        )

    return {
        "ok": True,
        "message": "ok",
        "image_path": str(out_path),
        "source_path": str(src),
        "source_name": src.name,
    }
    
def build_random_bottom_image_variant() -> dict:
    images = list_pool_bottom_images()
    if not images:
        return {
            "ok": False,
            "message": f"이미지 풀 폴더에 이미지가 없습니다: {BOTTOM_IMAGE_POOL_DIR}",
            "image_path": "",
        }
        
    src = _pick_source_bottom_image(images)
    BOTTOM_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    
    with Image.open(src) as img:
        img = img.convert("RGB")
        width, height = img.size
        
        # Resize slightly.
        ratio = random.uniform(0.97, 1.03)
        new_w = max(120, int(width * ratio))
        new_h = max(120, int(height * ratio))
        if new_w != width or new_h != height:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Apply subtle visual changes.
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Color(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Sharpness(img).enhance(random.uniform(0.99, 1.03))
        img = _mutate_pixels_lightly(img)
        
        out_name = f"{src.stem}_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
        out_path = BOTTOM_IMAGE_VARIANT_DIR / out_name
        img.save(
            out_path,
            format="JPEG",
            quality=random.randint(88, 94),
            optimize=True,
            progressive=True,
        )

    return {
        "ok": True,
        "message": "ok",
        "image_path": str(out_path),
        "source_path": str(src),
        "source_name": src.name,
    }

def build_random_hyper_image_variant() -> dict:
    images = list_pool_hyper_images()
    if not images:
        return {
            "ok": False,
            "message": f"이미지 풀 폴더에 이미지가 없습니다: {HYPER_IMAGE_POOL_DIR}",
            "image_path": "",
        }
        
    src = _pick_source_hyper_image(images)
    HYPER_IMAGE_VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    
    with Image.open(src) as img:
        img = img.convert("RGB")
        width, height = img.size
        
        # Resize slightly.
        ratio = random.uniform(0.97, 1.03)
        new_w = max(120, int(width * ratio))
        new_h = max(120, int(height * ratio))
        if new_w != width or new_h != height:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Apply subtle visual changes.
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Color(img).enhance(random.uniform(0.985, 1.02))
        img = ImageEnhance.Sharpness(img).enhance(random.uniform(0.99, 1.03))
        img = _mutate_pixels_lightly(img)
        
        out_name = f"{src.stem}_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
        out_path = HYPER_IMAGE_VARIANT_DIR / out_name
        img.save(
            out_path,
            format="JPEG",
            quality=random.randint(88, 94),
            optimize=True,
            progressive=True,
        )

    return {
        "ok": True,
        "message": "ok",
        "image_path": str(out_path),
        "source_path": str(src),
        "source_name": src.name,
    }
