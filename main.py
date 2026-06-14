import os
import time

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from services.app_logger import get_logger
from routers.admin.init import router as admin_router
from routers.scraper import router as scraper_router
from routers.user.init import router as user_router

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI()
logger = get_logger(__name__)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "change-this-session-secret"),
    same_site="lax",
    https_only=False,  # HTTPS 운영이면 True 권장
)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "http request method=%s path=%s status=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            getattr(response, "status_code", "unknown"),
            elapsed_ms,
        )
        return response
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        logger.exception(
            "http request failed method=%s path=%s elapsed_ms=%.2f",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise


app.include_router(admin_router)
app.include_router(user_router)
app.include_router(scraper_router)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html lang="ko">
    <head>
      <meta charset="UTF-8" />
      <title>피해 사례 자동화 MVP</title>
      <style>
        body {
          margin: 0;
          min-height: 100vh;
          display: grid;
          place-items: center;
          font-family: "Pretendard", "Noto Sans KR", sans-serif;
          background:
            radial-gradient(900px 380px at 10% -10%, #d9ecff 0%, transparent 60%),
            radial-gradient(760px 300px at 95% 0%, #d8f6f0 0%, transparent 55%),
            #f3f7fb;
          color: #1f2d3d;
        }

        .box {
          width: min(480px, calc(100vw - 32px));
          padding: 32px;
          border: 1px solid #d7e1ed;
          border-radius: 18px;
          background: linear-gradient(160deg, #fff 0%, #f7fbff 100%);
          box-shadow: 0 14px 40px rgba(20, 54, 90, 0.1);
          text-align: center;
        }

        h2 {
          margin: 0 0 10px;
          font-size: clamp(1.5rem, 1.1rem + 1.4vw, 2rem);
        }

        p {
          margin: 0 0 20px;
          color: #5d6b7a;
        }

        .actions {
          display: flex;
          justify-content: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        button {
          border: 1px solid transparent;
          border-radius: 999px;
          padding: 11px 18px;
          font-weight: 650;
          cursor: pointer;
        }
        
        #user-btn {
          margin-right: 10px;
        }
        
        #admin-btn {
          margin-left: 10px;
        }

        .btn-primary {
          color: #f8fbff;
          background: linear-gradient(135deg, #2f8be6 0%, #1b75d0 100%);
        }

        .btn-secondary {
          color: #204c78;
          border-color: #bdd4e8;
          background: linear-gradient(180deg, #fff 0%, #f3f8ff 100%);
        }
      </style>
    </head>
    <body>
      <div class="box">
        <h2>N 블로그 자동화</h2>
        <p>접속 유형을 선택하세요.</p>
        <button id="user-btn" onclick="location.href='/user'">일반 사용자 접속</button>
        <button id="admin-btn" onclick="location.href='/admin'">관리자 접속</button>
      </div>
    </body>
    </html>
    """