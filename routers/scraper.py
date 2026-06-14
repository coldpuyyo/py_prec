from fastapi import APIRouter

from services.app_logger import get_logger
from services.scrape_service import (
    scrape_cafes_by_category,
    scrape_naver_cafe_article,
    scrape_naver_cafe_list,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/scrape/category")
def scrape_category(category: str, limit: int = 10):
    logger.info("scrape_category start category=%s limit=%s", category, limit)
    try:
        results = scrape_cafes_by_category(
            category=category,
            limit_per_cafe=limit,
        )
        logger.info("scrape_category success category=%s count=%s", category, len(results))
        return {
            "message": "수집 완료",
            "category": category,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.exception("scrape_category failed category=%s", category)
        return {
            "message": "수집 실패",
            "error": str(e),
            "results": [],
        }


@router.get("/scrape/naver-cafe")
def scrape_naver_cafe(
    keyword: str = "사기 피해사례",
    limit: int = 20,
):
    url = "https://cafe.naver.com/f-e/cafes/25470135/menus/891?viewType=L"
    logger.info("scrape_naver_cafe start keyword=%s limit=%s", keyword, limit)

    try:
        results = scrape_naver_cafe_list(
            url=url,
            keyword=keyword,
            limit=limit,
        )
        logger.info("scrape_naver_cafe success keyword=%s count=%s", keyword, len(results))
        return {
            "message": "수집 완료",
            "keyword": keyword,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.exception("scrape_naver_cafe failed keyword=%s", keyword)
        return {
            "message": "수집 실패",
            "error": str(e),
            "results": [],
        }


@router.get("/scrape/naver-cafe/article")
def scrape_article(url: str):
    logger.info("scrape_article start url=%s", url)
    try:
        result = scrape_naver_cafe_article(url)
        logger.info("scrape_article success url=%s title_exists=%s", url, bool(result.get("title")))
        return {
            "message": "본문 수집 완료",
            "result": result,
        }
    except Exception as e:
        logger.exception("scrape_article failed url=%s", url)
        return {
            "message": "본문 수집 실패",
            "error": str(e),
        }
