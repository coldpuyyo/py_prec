from fastapi import FastAPI
from routers import blog, cardnews, page, thumbnail

app = FastAPI()

app.include_router(blog.router)
app.include_router(cardnews.router)
app.include_router(page.router)
app.include_router(thumbnail.router)

@app.get("/")
def home():
    return {"message": "피해 사례 자동화 MVP 시작"}