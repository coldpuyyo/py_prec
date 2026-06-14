import hmac
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"

# .env 강제 로드
load_dotenv(ENV_PATH)


def get_admin_credentials() -> tuple[str, str]:
    username = (os.getenv("ADMIN_USERNAME") or "").strip()
    password = (os.getenv("ADMIN_PASSWORD") or "").strip()

    # 운영 중 기본 계정으로 열리는 사고 방지
    if not username or not password:
        raise RuntimeError("ADMIN_USERNAME / ADMIN_PASSWORD가 .env에 설정되지 않았습니다.")

    return username, password


def verify_admin_credentials(username: str, password: str) -> bool:
    saved_username, saved_password = get_admin_credentials()
    return (
        hmac.compare_digest((username or "").strip(), saved_username)
        and hmac.compare_digest((password or "").strip(), saved_password)
    )


def is_admin_logged_in(session: dict) -> bool:
    return bool(session.get("admin_logged_in"))
