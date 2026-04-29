import os
from fastapi import APIRouter
from schemas import CaseInput, ThumbnailInput
from services.gemini_service import generate_text, generate_image

router = APIRouter()

@router.post("/thumbnail-text")
def generate_thumbnail_text(data: CaseInput):
    prompt = f"""
다음 피해 사례를 바탕으로 블로그/인스타 썸네일 제목을 만들어줘.

조건:
- 15자 이내
- 자극적이되 과장하지 않기
- 클릭하고 싶게 만들기
- 결과는 제목만 출력

피해 사례:
{data.text}
"""

    try:
        result = generate_text(prompt)
        return {"thumbnail_text": result.strip()}
    except Exception as e:
        return {"thumbnail_text": f"썸네일 문구 생성 실패: {str(e)}"}
    
@router.post("/thumbnail-image")
def generate_thumbnail_image(data: ThumbnailInput):
    os.makedirs("output/thumbnail", exist_ok=True)

    prompt = f"""
네이버 블로그 썸네일 이미지를 생성해줘.

주제:
{data.text}

스타일:
- 중고거래 사기 예방 콘텐츠
- 어두운 배경
- 긴장감 있는 분위기
- 스마트폰, 송금, 경고 아이콘 느낌
- 1080x1080 정사각형
- 이미지 안에 글자는 넣지 마
- 실제 사람 얼굴은 넣지 마
"""

    try:
        file_path = "output/thumbnail/thumbnail_ai.png"
        saved_path = generate_image(prompt, file_path)

        return {
            "message": "AI 썸네일 이미지 생성 완료",
            "file": saved_path
        }

    except Exception as e:
        return {
            "message": "AI 썸네일 이미지 생성 실패",
            "error": str(e)
        }