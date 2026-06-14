from __future__ import annotations

import re


def _looks_like_subtitle_paragraph(p: str) -> bool:
    raw = (p or "").strip()
    if not raw:
        return False
    
    # * 소제목 형태는 별표 제거 전에 먼저 검사해야 함
    if re.match(r"^\*\s+\S+", raw):
        cleaned = re.sub(r"^\*\s+", "", raw).strip()
        if 2 <= len(cleaned) <= 60:
            return True

    # 0) **소제목** / __소제목__ 형태 우선 인식
    if re.match(r"^\*\*[^*\n]{2,100}\*\*$", raw):
        return True
    if re.match(r"^__[^_\n]{2,100}__$", raw):
        return True

    # 중요: 이 줄이 반드시 '주석 밖'에 있어야 함
    t = re.sub(r"^[`*_~\s]+|[`*_~\s]+$", "", raw).strip()
    if not t:
        return False

    if len(t) > 60:
        return False

    # 1) markdown heading
    if re.match(r"^#{1,6}\s+\S+", t):
        return True

    # 2) [제목]
    if re.match(r"^\[[^\]]{1,50}\]$", t):
        return True

    # 3) 번호 소제목: 1. 제목 / 1) 제목
    if re.match(r"^\d{1,2}[.)]\s+\S+", t):
        return True

    # 4) 키워드형
    if re.match(r"^(서론|본론|결론|요약|마무리|핵심\s*정리|핵심\s*포인트)\s*[:：]?$", t):
        return True

    return False


def _split_content_for_subtitle_sections(content: str) -> tuple[str, list[str]]:
    text = str(content or "").strip()
    if not text:
        return "", []

    lines = text.splitlines()
    if not lines:
        return text, []

    intro_lines: list[str] = []
    sections: list[str] = []
    current_section: list[str] = []
    in_section = False

    def flush_section():
        nonlocal current_section
        block = "\n".join(current_section).strip()
        if block:
            sections.append(block)
        current_section = []

    for raw in lines:
        line = raw.rstrip("\r")
        s = line.strip()

        # 빈 줄 처리
        if not s:
            if in_section:
                if current_section and current_section[-1] != "":
                    current_section.append("")
            else:
                if intro_lines and intro_lines[-1] != "":
                    intro_lines.append("")
            continue

        # 소제목 시작 감지
        if _looks_like_subtitle_paragraph(s):
            if in_section:
                flush_section()
            else:
                in_section = True
            current_section = [s]
            continue

        # 일반 본문 라인
        if in_section:
            current_section.append(s)
        else:
            intro_lines.append(s)

    if in_section:
        flush_section()

    intro = "\n".join(intro_lines).strip()

    # 소제목이 없으면 기존처럼 intro 전체만 반환
    if not sections:
        return text, []

    # 중요: 첫 소제목을 intro로 빼지 않음 (기존 pop 제거)
    return intro, sections


def _plain_heading_text(value: str) -> str:
    t = str(value or "").strip()
    t = re.sub(r"^#{1,6}\s*", "", t).strip()
    t = re.sub(r"^[`*_~\s]+|[`*_~\s]+$", "", t).strip()
    t = t.strip("[]() ")
    return t


def _clean_publish_subtitle_text(value: str) -> str:
    original = str(value or "").strip()
    if not original:
        return ""

    text = original
    wrapper_patterns = [
        r"^\*\*(?P<text>[^*\n].*?)\*\*$",
        r"^__(?P<text>[^_\n].*?)__$",
        r"^\[(?P<text>[^\[\]\n]+)\]$",
        r"^\((?P<text>[^()\n]+)\)$",
        r'^"(?P<text>[^"\n]+)"$',
    ]

    for _ in range(4):
        before = text
        text = re.sub(r"^#{1,6}\s+", "", text).strip()
        text = re.sub(r"^(?:[*\-\u2022]\s+|\d{1,2}[.)]\s+)", "", text).strip()

        for pattern in wrapper_patterns:
            match = re.match(pattern, text)
            if match:
                text = match.group("text").strip()
                break

        if text == before:
            break

    return text or original


def _is_hashtag_line(line: str) -> bool:
    s = str(line or "").strip()
    if not s:
        return False

    # "# 제목" / "### 제목" 형태는 마크다운 제목으로 보고 해시태그 제외
    if re.match(r"^#{1,6}\s+\S+", s):
        return False

    # "#태그#태그", "#태그 #태그", "#법률 조력#피해 구제" 같은 사용자 입력도 해시태그 줄로 처리
    return s.startswith("#") and len(s) > 1


def _is_closing_title(line: str) -> bool:
    t = _plain_heading_text(line)
    if not t or len(t) > 40:
        return False

    closing_words = ["결론", "마무리", "요약", "정리", "최종 정리"]
    return any(word in t for word in closing_words)


def _split_subtitle_block(block: str) -> tuple[str, str]:
    raw_lines = str(block or "").splitlines()
    if not raw_lines:
        return "", ""

    title_idx = None
    for idx, line in enumerate(raw_lines):
        if line.strip():
            title_idx = idx
            break

    if title_idx is None:
        return "", ""

    subtitle = _clean_publish_subtitle_text(raw_lines[title_idx])
    body_lines = raw_lines[title_idx + 1:]

    # 앞뒤 빈 줄만 제거하고, 내부 빈 줄은 문단 구분용으로 보존
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    body = "\n".join(body_lines).strip()
    return subtitle, body


def _split_last_paragraph(text: str, conclusion_paragraph_count: int = 1) -> tuple[str, str]:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return "", ""

    try:
        count = max(0, min(10, int(conclusion_paragraph_count or 0)))
    except Exception:
        count = 1

    if count <= 0:
        return raw, ""

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]

    if len(paragraphs) > count:
        body = "\n\n".join(paragraphs[:-count]).strip()
        closing = "\n\n".join(paragraphs[-count:]).strip()
        return body, closing

    return raw, ""


def _split_tail_hashtags(text: str) -> tuple[str, str]:
    lines = str(text or "").splitlines()
    hashtags: list[str] = []

    while lines and not lines[-1].strip():
        lines.pop()

    while lines and _is_hashtag_line(lines[-1]):
        hashtags.insert(0, lines.pop().strip())
        while lines and not lines[-1].strip():
            lines.pop()

    return "\n".join(lines).strip(), "\n".join(hashtags).strip()


def _split_publish_parts(content: str, conclusion_paragraph_count: int = 1) -> tuple[str, list[str], str, str]:
    text, hashtags = _split_tail_hashtags(content)
    intro, sections = _split_content_for_subtitle_sections(text)

    if not sections:
        return intro, [], "", hashtags

    last_title, last_body = _split_subtitle_block(sections[-1])

    # 1) 마지막 섹션 자체가 결론 제목이면 기존처럼 분리
    if _is_closing_title(last_title):
        closing = sections[-1].strip()
        return intro, sections[:-1], closing, hashtags

    # 2) 마지막 섹션 본문 안에 결론 제목이 있으면 기존처럼 분리
    body_lines = last_body.splitlines()
    for idx, line in enumerate(body_lines):
        if _is_closing_title(line):
            before_body = "\n".join(body_lines[:idx]).strip()
            closing = "\n".join(body_lines[idx:]).strip()

            new_sections = sections[:-1]
            rebuilt_last = "\n".join([last_title, before_body]).strip()
            if rebuilt_last:
                new_sections.append(rebuilt_last)

            return intro, new_sections, closing, hashtags

    # 3) 결론 제목이 없어도 마지막 섹션의 마지막 문단을 결론으로 분리
    before_body, inferred_closing = _split_last_paragraph(
        last_body,
        conclusion_paragraph_count=conclusion_paragraph_count,
    )
    if inferred_closing:
        new_sections = sections[:-1]
        rebuilt_last = "\n".join([last_title, before_body]).strip()
        if rebuilt_last:
            new_sections.append(rebuilt_last)

        return intro, new_sections, inferred_closing, hashtags

    return intro, sections, "", hashtags
