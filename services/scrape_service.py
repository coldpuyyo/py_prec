from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from services.app_logger import get_logger
from services.cafe_service import get_cafes_by_category, load_cafes
from services.naver_context_service import open_naver_context
from services.naver_login_service import ensure_naver_login

logger = get_logger(__name__)


def _normalize_article_text(text: str) -> str:
    cleaned = (text or "").replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", cleaned)
    lines = [line.strip() for line in cleaned.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def _remove_noise_nodes(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "iframe"]):
        tag.decompose()


def _extract_meta_content(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    if not el:
        return ""
    return str(el.get("content") or "").strip()


def _extract_blog_title(soup: BeautifulSoup) -> str:
    for selector in (
        "meta[property='og:title']",
        "meta[name='twitter:title']",
    ):
        value = _extract_meta_content(soup, selector)
        if value:
            return _normalize_article_text(value)

    for selector in (
        ".se-title-text",
        ".pcol1.itemSubjectBoldfont",
        ".tit_h3",
        "h1",
        "h2",
        "title",
    ):
        el = soup.select_one(selector)
        if not el:
            continue
        value = _normalize_article_text(el.get_text("\n", strip=True))
        if value:
            return value

    return ""


def _best_text_from_selectors(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str:
    best = ""
    for selector in selectors:
        for el in soup.select(selector):
            text = _normalize_article_text(el.get_text("\n", strip=True))
            if len(text) > len(best):
                best = text
    return best


def _extract_blog_article_from_html(html: str, is_naver_blog: bool) -> dict:
    soup = BeautifulSoup(html or "", "html.parser")
    _remove_noise_nodes(soup)

    title = _extract_blog_title(soup)

    naver_selectors = (
        ".se-main-container",
        "#postViewArea",
        "#postListBody",
    )
    generic_selectors = (
        "article",
        "main",
        "[role='main']",
        ".entry-content",
        ".post-content",
        ".post",
        ".article",
        "body",
    )

    selectors = naver_selectors + generic_selectors if is_naver_blog else generic_selectors
    content = _best_text_from_selectors(soup, selectors)
    if title and content.startswith(title):
        content = content[len(title):].strip()

    return {
        "title": title,
        "content": _normalize_article_text(content),
    }


def _validate_public_blog_url(url: str):
    target_url = (url or "").strip()
    if not target_url:
        raise ValueError("블로그 URL을 입력하세요.")

    parsed = urlparse(target_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("http 또는 https로 시작하는 공개 블로그 URL을 입력하세요.")

    return target_url, parsed


def _is_naver_blog_host(host: str) -> bool:
    normalized = (host or "").lower()
    return normalized in ("blog.naver.com", "m.blog.naver.com")


def _is_login_page(page) -> bool:
    url = (page.url or "").lower()
    if "nid.naver.com/nidlogin.login" in url:
        return True
    if page.locator("input#id").count() > 0 and page.locator("input#pw").count() > 0:
        return True
    return False


def scrape_blog_article(url: str) -> dict:
    target_url, parsed = _validate_public_blog_url(url)
    is_naver_blog = _is_naver_blog_host(parsed.netloc)

    logger.info(
        "scrape_blog_article start url=%s is_naver_blog=%s",
        target_url,
        is_naver_blog,
    )

    with sync_playwright() as p:
        with open_naver_context(
            p,
            member_required=False,
            naver_account_key="",
            profile_role="scraper",
            headless=True,
        ) as context:
            page = context.new_page()
            response = page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)

            if response is not None and response.status >= 400:
                logger.warning(
                    "scrape_blog_article http error url=%s status=%s",
                    target_url,
                    response.status,
                )
                return {"title": "접근 불가", "url": target_url, "content": ""}

            if _is_login_page(page):
                logger.warning("scrape_blog_article login page detected url=%s", page.url)
                return {"title": "접근 불가", "url": target_url, "content": ""}

            html_candidates: list[str] = []
            if is_naver_blog:
                main_frame = page.frame(name="mainFrame")
                if main_frame is not None:
                    html_candidates.append(main_frame.content())

            html_candidates.append(page.content())

            best_article = {"title": "", "content": ""}
            for html in html_candidates:
                article = _extract_blog_article_from_html(html, is_naver_blog)
                if len(article.get("content", "")) > len(best_article.get("content", "")):
                    best_article = article

            title = best_article.get("title", "")
            content = best_article.get("content", "")
            logger.info(
                "scrape_blog_article done url=%s title_len=%s content_len=%s",
                target_url,
                len(title or ""),
                len(content or ""),
            )

            return {
                "title": title,
                "url": target_url,
                "content": content,
            }


def _extract_cafe_id(url: str) -> str:
    m = re.search(r"/cafes/(\d+)/", url or "")
    return m.group(1) if m else ""


def _resolve_member_policy_from_article_url(url: str) -> tuple[bool, str]:
    cafe_id = _extract_cafe_id(url)
    if not cafe_id:
        return False, ""

    for cafe in load_cafes():
        if f"/cafes/{cafe_id}/" in (cafe.get("url") or ""):
            return bool(cafe.get("member_required", False)), str(
                cafe.get("scraper_profile_key") or cafe.get("naver_account_key") or ""
            ).strip()

    return False, ""


def scrape_cafes_by_category(category: str, limit_per_cafe: int = 10) -> list[dict]:
    logger.info("scrape_cafes_by_category start category=%s limit_per_cafe=%s", category, limit_per_cafe)
    cafes = get_cafes_by_category(category)
    all_results: list[dict] = []

    for cafe in cafes:
        filter_type = cafe.get("filter_type", "keyword")
        member_required = bool(cafe.get("member_required", False))
        naver_account_key = str(cafe.get("scraper_profile_key") or cafe.get("naver_account_key") or "").strip()

        logger.info(
            "scrape_cafes_by_category cafe start name=%s filter_type=%s member_required=%s account_key=%s",
            cafe.get("name", ""),
            filter_type,
            member_required,
            naver_account_key,
        )
        
        if filter_type == "exclude":
            results = scrape_naver_cafe_list(
                url=cafe["url"],
                exclude=cafe.get("exclude", []),
                limit=limit_per_cafe,
                member_required=member_required,
                naver_account_key=naver_account_key,
                profile_role="scraper",
            )
        else:
            results = scrape_naver_cafe_list(
                url=cafe["url"],
                keyword=cafe.get("keyword", ""),
                limit=limit_per_cafe,
                member_required=member_required,
                naver_account_key=naver_account_key,
                profile_role="scraper",
            )

        for item in results:
            item["cafe_name"] = cafe.get("name", "")
            item["category"] = cafe.get("category", category)
            item["member_required"] = member_required
            item["scraper_profile_key"] = naver_account_key
            item["naver_account_key"] = naver_account_key

        all_results.extend(results)
        logger.info(
            "scrape_cafes_by_category cafe done name=%s result_count=%s",
            cafe.get("name", ""),
            len(results),
        )
        
    logger.info("scrape_cafes_by_category done category=%s total_count=%s", category, len(all_results))
    return all_results


def scrape_naver_cafe_list(
    url: str,
    limit: int = 20,
    keyword: str = "",
    exclude: list[str] | None = None,
    member_required: bool = False,
    naver_account_key: str = "",
    profile_role: str = "scraper",
) -> list[dict]:
    if exclude is None:
        exclude = []
        
    logger.info(
        "scrape_naver_cafe_list start url=%s limit=%s keyword=%s exclude_count=%s member_required=%s account_key=%s role=%s",
        url,
        limit,
        keyword,
        len(exclude),
        member_required,
        naver_account_key,
        profile_role,
    )

    results: list[dict] = []

    with sync_playwright() as p:
        with open_naver_context(
            p,
            member_required=member_required,
            naver_account_key=naver_account_key,
            profile_role=profile_role,
            headless=(not member_required),
        ) as context:
            if member_required:
                login_ok, login_reason = ensure_naver_login(
                    context,
                    naver_account_key,
                    expected_role=profile_role,
                )
                logger.info(
                    "scrape_naver_cafe_list login result ok=%s reason=%s",
                    login_ok,
                    login_reason,
                )
                if not login_ok:
                    raise RuntimeError(f"카페 스크랩 로그인 실패: {login_reason}")

            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            logger.info("scrape_naver_cafe_list loaded page url=%s", page.url)

            if member_required and _is_login_page(page):
                relog_ok, relog_reason = ensure_naver_login(
                    context,
                    naver_account_key,
                    expected_role=profile_role,
                )
                logger.info(
                    "scrape_naver_cafe_list relogin result ok=%s reason=%s",
                    relog_ok,
                    relog_reason,
                )
                if not relog_ok:
                    raise RuntimeError(f"카페 스크랩 재로그인 실패: {relog_reason}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)
                if _is_login_page(page):
                    raise RuntimeError(f"로그인 후에도 접근 불가: {naver_account_key or 'default'}")

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            rows = soup.select("tr")
            links = soup.find_all("a")
            logger.info("scrape_naver_cafe_list parsed rows=%s links=%s", len(rows), len(links))
            
            if exclude:
                for row in rows:
                    row_text = row.get_text(" ", strip=True)
                    if any(author in row_text for author in exclude):
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
                    if "articles" not in href:
                        continue
                    if keyword and keyword not in title:
                        continue

                    if href.startswith("/"):
                        href = "https://cafe.naver.com" + href

                    if any(item["url"] == href for item in results):
                        continue

                    results.append({"title": title, "url": href})
                    if len(results) >= limit:
                        break
            else:
                for a in links:
                    title = a.get_text(" ", strip=True)
                    href = a.get("href")

                    if not title or not href:
                        continue
                    if "commentFocus" in href:
                        continue
                    if "articles" not in href:
                        continue
                    if keyword and keyword not in title:
                        continue

                    if href.startswith("/"):
                        href = "https://cafe.naver.com" + href

                    if any(item["url"] == href for item in results):
                        continue

                    results.append({"title": title, "url": href})
                    if len(results) >= limit:
                        break
    logger.info("scrape_naver_cafe_list done result_count=%s", len(results))
    return results


def scrape_naver_cafe_article(
    url: str,
    member_required: bool | None = None,
    naver_account_key: str | None = None,
) -> dict:
    logger.info(
        "scrape_naver_cafe_article start url=%s member_required=%s account_key=%s",
        url,
        member_required,
        naver_account_key,
    )
    
    if member_required is None or naver_account_key is None:
        inferred_member_required, inferred_key = _resolve_member_policy_from_article_url(url)
        if member_required is None:
            member_required = inferred_member_required
        if naver_account_key is None:
            naver_account_key = inferred_key
            
    logger.info(
        "scrape_naver_cafe_article resolved member_required=%s account_key=%s",
        member_required,
        naver_account_key,
    )
    
    with sync_playwright() as p:
        with open_naver_context(
            p,
            member_required=bool(member_required),
            naver_account_key=str(naver_account_key or ""),
            profile_role="scraper",
            headless=(not bool(member_required)),
        ) as context:
            if bool(member_required):
                login_ok, _ = ensure_naver_login(
                    context,
                    str(naver_account_key or ""),
                    expected_role="scraper",
                )
                logger.info(
                    "scrape_naver_cafe_article login result ok=%s reason=%s",
                    login_ok,
                )
                if not login_ok:
                    logger.warning("scrape_naver_cafe_article access denied by login failure")
                    return {
                        "title": "접근 불가",
                        "url": url,
                        "content": "",
                    }

            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2000)
            logger.info("scrape_naver_cafe_article loaded page url=%s", page.url)

            if member_required and _is_login_page(page):
                relog_ok, _ = ensure_naver_login(
                    context,
                    str(naver_account_key or ""),
                    expected_role="scraper",
                )
                logger.info(
                    "scrape_naver_cafe_article relogin result ok=%s reason=%s",
                    relog_ok,
                )
                if relog_ok:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2000)

            if member_required and _is_login_page(page):
                logger.warning("scrape_naver_cafe_article still on login page")
                return {
                    "title": "접근 불가",
                    "url": url,
                    "content": "",
                }

            frame = page.frame(name="cafe_main")
            if frame is None:
                logger.warning("scrape_naver_cafe_article frame missing url=%s", page.url)
                return {
                    "title": "접근 불가",
                    "url": url,
                    "content": "",
                }

            html = frame.content()
            soup = BeautifulSoup(html, "html.parser")

            title_el = soup.select_one("h3.title_text")
            content_el = soup.select_one(".se-main-container")

            title = title_el.get_text(" ", strip=True) if title_el else ""
            content = content_el.get_text("\n", strip=True) if content_el else ""

            content = content.replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")
            content = re.split(r"\n\s*\n\s*\n", content)[0].strip()
            if title:
                content = content.replace(title, "", 1).strip()

            logger.info(
                "scrape_naver_cafe_article done title_len=%s content_len=%s",
                len(title or ""),
                len(content or ""),
            )
            
            return {
                "title": title,
                "url": url,
                "content": content,
            }
