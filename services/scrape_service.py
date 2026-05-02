from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

from services.cafe_service import get_cafes_by_category

def scrape_cafes_by_category(category: str, limit_per_cafe: int = 10):
    cafes = get_cafes_by_category(category)

    all_results = []

    for cafe in cafes:
        filter_type = cafe.get("filter_type", "keyword")

        if filter_type == "exclude_author":
            results = scrape_naver_cafe_list(
                url=cafe["url"],
                exclude_authors=cafe.get("exclude_authors", []),
                limit=limit_per_cafe
            )
        else:
            results = scrape_naver_cafe_list(
                url=cafe["url"],
                keyword=cafe.get("keyword", ""),
                limit=limit_per_cafe
            )

        for item in results:
            item["cafe_name"] = cafe["name"]
            item["category"] = cafe["category"]

        all_results.extend(results)

    return all_results

def scrape_naver_cafe_list( url: str, limit: int = 20, keyword: str = "", exclude_authors: list[str] = None):
    if exclude_authors is None:
        exclude_authors = []

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            rows = soup.select("tr")
            links = soup.find_all("a")

            # 1) 작성자 필터 우선: 게시판 row 기준
            if exclude_authors:
                for row in rows:
                    row_text = row.get_text(" ", strip=True)

                    if any(author in row_text for author in exclude_authors):
                        continue

                    a = row.find("a", href=True)
                    if not a:
                        continue

                    title = a.get_text(" ", strip=True)
                    href = a.get("href")

                    if not title or not href:
                        continue

                    if "commentFocus" in href:
                        continue

                    if title.startswith("댓글수"):
                        continue

                    if "articles" not in href:
                        continue

                    if keyword and keyword not in title:
                        continue

                    if href.startswith("/"):
                        href = "https://cafe.naver.com" + href

                    if any(item["url"] == href for item in results):
                        continue

                    results.append({
                        "title": title,
                        "url": href
                    })

                    if len(results) >= limit:
                        break

            # 2) 키워드 필터
            else:
                for a in links:
                    title = a.get_text(" ", strip=True)
                    href = a.get("href")

                    if not title or not href:
                        continue

                    if "commentFocus" in href:
                        continue

                    if title.startswith("댓글수"):
                        continue

                    if "articles" not in href:
                        continue

                    if keyword and keyword not in title:
                        continue

                    if href.startswith("/"):
                        href = "https://cafe.naver.com" + href

                    if any(item["url"] == href for item in results):
                        continue

                    results.append({
                        "title": title,
                        "url": href
                    })

                    if len(results) >= limit:
                        break

        finally:
            browser.close()

    return results

def scrape_naver_cafe_article(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            # 🔥 iframe 찾기
            frame = page.frame(name="cafe_main")

            if frame is None:
                return {
                    "title": "iframe 못찾음",
                    "url": url,
                    "content": ""
                }

            html = frame.content()
            soup = BeautifulSoup(html, "html.parser")

            title_el = soup.select_one("h3.title_text")
            content_el = soup.select_one(".se-main-container")

            title = title_el.get_text(" ", strip=True) if title_el else ""
            content = content_el.get_text("\n", strip=True) if content_el else ""
            # 특수 공백 제거
            content = content.replace("\u200b", "")
            content = content.replace("\ufeff", "")
            content = content.replace("\xa0", " ")

            # 줄바꿈 3개 이상 이후 내용 제거
            content = re.split(r"\n\s*\n\s*\n", content)[0].strip()
            
            content = content.replace(title, "")

            return {
                "title": title,
                "url": url,
                "content": content
            }

        finally:
            browser.close()