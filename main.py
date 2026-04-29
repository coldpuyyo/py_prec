from fastapi import FastAPI
from routers import blog, page, admin, user, scraper

app = FastAPI()

app.include_router(blog.router)
app.include_router(page.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(scraper.router)

@app.get("/")
def home():
    return {"message": "피해 사례 자동화 MVP 시작"}