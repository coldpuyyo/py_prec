from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

def scrape_naver_cafe_list(url: str, limit: int = 20, keyword: str = "투자사기 피해사례"):
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

            links = soup.find_all("a")

            for a in links:
                title = a.get_text(" ", strip=True)
                href = a.get("href")

                if not title or not href:
                    continue

                # 댓글 링크 제거
                if "commentFocus" in href:
                    continue

                # 댓글수 텍스트 제거
                if title.startswith("댓글수"):
                    continue

                # 게시글 링크만
                if "articles" not in href:
                    continue

                # 원하는 키워드 포함 글만
                if keyword not in title:
                    continue

                if href.startswith("/"):
                    href = "https://cafe.naver.com" + href

                # 중복 제거
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