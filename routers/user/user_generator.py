# C:\Users\Cold_Puyo\Documents\Py_prec\routers\user\user_generator.py
from fastapi import APIRouter

from schemas.user import GenerateRequest, TitleGenerateRequest
from services.ai_runtime import get_supported_models
from services.ai_service import generate_text
from services.prompt_service import (
    load_scrapgenarator_prompt,
    load_keywordgenarator_prompt,
    load_blogscrapgenarator_prompt,
    load_titlegenarator_prompt,
)
from services.scrape_service import scrape_blog_article, scrape_naver_cafe_article
from services.app_logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _resolve_provider_model(provider: str, model: str | None):
    selected_provider = (provider or "gemini").strip().lower()
    selected_model = (model or "").strip()

    supported_models = get_supported_models(selected_provider)
    if selected_model and selected_model not in supported_models:
        return None, None, f"에러 발생: 지원하지 않는 모델입니다. ({selected_provider}: {selected_model})"

    if not selected_model and supported_models:
        selected_model = supported_models[0]

    return selected_provider, selected_model, None


def _safe_prompt_format(template: str, **kwargs) -> str:
    try:
        return template.format(**kwargs)
    except Exception:
        # 프롬프트에 중괄호가 섞여 있어 format 에러가 나도 기본 치환은 되게 처리
        result = str(template)
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result


@router.post("/user/scrapgenerate")
def generate_blog(data: GenerateRequest):
    logger.info(
        "generate_blog start provider=%s model=%s has_url=%s length=%s",
        data.provider,
        data.model,
        bool(data.url),
        data.length,
    )
    try:
        prompt_data = load_scrapgenarator_prompt()

        case_text = ""
        if data.url:
            article = scrape_naver_cafe_article(data.url)
            title = (article.get("title") or "").strip()
            content = (article.get("content") or "").strip()

            if not title or not content:
                logger.warning("generate_blog scraped article empty url=%s", data.url)
                return {"result": "수집된 글이 없습니다. 다른 URL을 선택해 주세요."}

            case_text = content

        prompt = _safe_prompt_format(
            prompt_data.get("blog_prompt", ""),
            case=case_text,
            sub_input=data.subInput,
            sub_title=data.subTitle,
            length=data.length,
        )

        provider, model, model_error = _resolve_provider_model(data.provider, data.model)
        if model_error:
            logger.warning("generate_blog model validation failed: %s", model_error)
            return {"result": model_error}

        result = generate_text(prompt, provider=provider, model=(model or None))
        logger.info("generate_blog success provider=%s model=%s result_len=%s", provider, model, len(result or ""))
        return {"result": result}

    except Exception as e:
        logger.exception("generate_blog failed")
        return {"result": f"에러 발생: {str(e)}"}


@router.post("/user/keywordgenerate")
def generate_keywords(data: GenerateRequest):
    logger.info(
        "generate_keywords start provider=%s model=%s keywords=%s length=%s",
        data.provider,
        data.model,
        bool(data.keywords),
        data.length,
    )
    try:
        prompt_data = load_keywordgenarator_prompt()

        prompt = _safe_prompt_format(
            prompt_data.get("blog_prompt", ""),
            keywords=data.keywords,
            sub_input=data.subInput,
            sub_title=data.subTitle,
            length=data.length,
        )

        provider, model, model_error = _resolve_provider_model(data.provider, data.model)
        if model_error:
            logger.warning("generate_keywords model validation failed: %s", model_error)
            return {"result": model_error}

        result = generate_text(prompt, provider=provider, model=(model or None))
        logger.info("generate_keywords success provider=%s model=%s result_len=%s", provider, model, len(result or ""))
        return {"result": result}

    except Exception as e:
        logger.exception("generate_keywords failed")
        return {"result": f"에러 발생: {str(e)}"}


@router.post("/user/blogscrapgenerate")
def generate_blog_scrap(data: GenerateRequest):
    logger.info(
        "generate_blog_scrap start provider=%s model=%s has_url=%s length=%s",
        data.provider,
        data.model,
        bool(data.url),
        data.length,
    )
    try:
        url = (data.url or "").strip()
        if not url:
            return {"result": "에러 발생: 블로그 URL을 입력하세요."}

        prompt_data = load_blogscrapgenarator_prompt()
        article = scrape_blog_article(url)
        title = (article.get("title") or "").strip()
        content = (article.get("content") or "").strip()

        if not content:
            logger.warning("generate_blog_scrap scraped article empty url=%s", url)
            return {"result": "수집된 글이 없습니다. 공개 블로그 글 URL인지 확인해 주세요."}

        case_text = f"제목:\n{title}\n\n본문:\n{content}" if title else content
        prompt = _safe_prompt_format(
            prompt_data.get("blog_prompt", ""),
            case=case_text,
            sub_input=data.subInput,
            sub_title=data.subTitle,
            length=data.length,
        )

        provider, model, model_error = _resolve_provider_model(data.provider, data.model)
        if model_error:
            logger.warning("generate_blog_scrap model validation failed: %s", model_error)
            return {"result": model_error}

        result = generate_text(prompt, provider=provider, model=(model or None))
        logger.info("generate_blog_scrap success provider=%s model=%s result_len=%s", provider, model, len(result or ""))
        return {"result": result}

    except Exception as e:
        logger.exception("generate_blog_scrap failed")
        return {"result": f"에러 발생: {str(e)}"}


@router.post("/user/titlegenerate")
def generate_title(data: TitleGenerateRequest):
    logger.info(
        "generate_title start provider=%s model=%s case_len=%s",
        data.provider,
        data.model,
        len((data.case or "").strip()),
    )
    try:
        case_text = (data.case or "").strip()
        if not case_text:
            return {"result": "에러 발생: 제목 생성을 위한 본문이 비어 있습니다."}

        prompt_data = load_titlegenarator_prompt()
        title_prompt = str(prompt_data.get("title_prompt", "")).strip()
        if not title_prompt:
            return {"result": "에러 발생: titlegenarator_prompt.json 의 title_prompt 가 비어 있습니다."}

        detail_input = (data.subInput or data.subInput2 or "").strip()
        prompt = _safe_prompt_format(
            title_prompt,
            case=case_text,
            sub_input=detail_input,
            sub_input2=detail_input,
        )

        provider, model, model_error = _resolve_provider_model(data.provider, data.model)
        if model_error:
            logger.warning("generate_title model validation failed: %s", model_error)
            return {"result": model_error}

        result = generate_text(prompt, provider=provider, model=(model or None))
        logger.info("generate_title success provider=%s model=%s result_len=%s", provider, model, len(result or ""))
        return {"result": result}

    except Exception as e:
        logger.exception("generate_title failed")
        return {"result": f"에러 발생: {str(e)}"}
