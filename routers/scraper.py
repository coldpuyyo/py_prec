from fastapi import APIRouter
from services.scrape_service import scrape_naver_cafe_list, scrape_naver_cafe_article, scrape_cafes_by_category

router = APIRouter()

@router.get("/scrape/category")
def scrape_category(category: str, limit: int = 10):
    try:
        results = scrape_cafes_by_category(
            category=category,
            limit_per_cafe=limit
        )

        return {
            "message": "카테고리별 수집 완료",
            "category": category,
            "count": len(results),
            "results": results
        }

    except Exception as e:
        return {
            "message": "카테고리별 수집 실패",
            "error": str(e)
        }

@router.get("/scrape/naver-cafe")
def scrape_naver_cafe(keyword: str = "투자사기 피해사례", limit: int = 20):
    url = "https://cafe.naver.com/f-e/cafes/25470135/menus/891?viewType=L"

    try:
        results = scrape_naver_cafe_list(
            url=url,
            keyword=keyword,
            limit=limit
        )

        return {
            "message": "수집 완료",
            "keyword": keyword,
            "count": len(results),
            "results": results
        }

    except Exception as e:
        return {
            "message": "수집 실패",
            "error": str(e)
        }
        
@router.get("/scrape/naver-cafe/article")
def scrape_article(url: str):
    try:
        result = scrape_naver_cafe_article(url)

        return {
            "message": "본문 수집 완료",
            "result": result
        }

    except Exception as e:
        return {
            "message": "본문 수집 실패",
            "error": str(e)
        }