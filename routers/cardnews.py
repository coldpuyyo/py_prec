from fastapi import APIRouter
from schemas import CaseInput, CardNewsInput
from services.gemini_service import generate_text
from services.image_service import create_cardnews_images

router = APIRouter()

@router.post("/cardnews")
def generate_cardnews(data: CaseInput):
    prompt = f"""
다음 피해 사례를 카드뉴스 5장 문구로 만들어줘.

반드시 아래 형식만 출력해.
설명문, 인사말, 해시태그, 구분선은 쓰지 마.

[1장]
제목:
본문:

[2장]
제목:
본문:

[3장]
제목:
본문:

[4장]
제목:
본문:

[5장]
제목:
본문:

조건:
- 제목은 15자 이내
- 본문은 35자 이내
- 강렬하고 짧게
- 인스타 카드뉴스 스타일
- 과장 광고처럼 보이지 않게

피해 사례:
{data.text}
"""

    try:
        result = generate_text(prompt)
        return {"cardnews": result}
    except Exception as e:
        return {"cardnews": f"카드뉴스 생성 실패: {str(e)}"}

@router.post("/cardnews-image")
def generate_cardnews_image(data: CardNewsInput):
    try:
        files = create_cardnews_images(data.text)
        return {
            "message": "카드뉴스 이미지 생성 완료",
            "files": files
        }
    except Exception as e:
        return {
            "message": "카드뉴스 이미지 생성 실패",
            "error": str(e)
        }