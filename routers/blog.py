from fastapi import APIRouter
from schemas import CaseInput, BlogSaveInput
from services.gemini_service import generate_text
from services.file_service import save_blog_file

router = APIRouter()

@router.post("/blog")
def generate_blog(data: CaseInput):
    prompt = f"""
다음 피해 사례를 바탕으로 블로그 글을 작성해줘.

조건:
- 제목 포함
- 서론 / 본문 / 결론 구조
- 길이: 800~1200자
- 중복 표현 제거
- 가독성 좋게 (짧은 문단)
- 감정 + 정보 균형
- 마지막에 해시태그 5개

피해 사례:
{data.text}
"""

    try:
        result = generate_text(prompt)
        return {"blog": result}
    except Exception as e:
        return {"blog": f"블로그 글 생성 실패: {str(e)}"}

@router.post("/save-blog")
def save_blog(data: BlogSaveInput):
    try:
        file_path = save_blog_file(data.title, data.content)
        return {
            "message": "블로그 글 저장 완료",
            "file": file_path
        }
    except Exception as e:
        return {
            "message": "블로그 글 저장 실패",
            "error": str(e)
        }