# services/ai_service.py
from __future__ import annotations

from google import genai
from openai import OpenAI

from services.ai_runtime import GEMINI_DEFAULT_MODEL, GPT_DEFAULT_MODEL, get_api_key


def generate_text(prompt: str, provider: str = "gemini", model: str | None = None) -> str:
    selected = (provider or "gemini").lower()

    if selected == "gemini":
        api_key = get_api_key("gemini")
        if not api_key:
            raise RuntimeError("Gemini API 키가 설정되지 않았습니다.")
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model or GEMINI_DEFAULT_MODEL,
            contents=prompt,
        )
        return (resp.text or "").strip()

    if selected in {"gpt", "openai"}:
        api_key = get_api_key("gpt")
        if not api_key:
            raise RuntimeError("OpenAI API 키가 설정되지 않았습니다.")
        client = OpenAI(api_key=api_key)
        resp = client.responses.create(
            model=model or GPT_DEFAULT_MODEL,
            input=prompt,
        )
        return (getattr(resp, "output_text", "") or "").strip()

    raise RuntimeError(f"지원하지 않는 provider: {selected}")
