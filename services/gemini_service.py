from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

def generate_text(prompt: str, model: str = "gemini-3-flash-preview") -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text

def generate_image(prompt: str, file_path: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt],
    )

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            image.save(file_path)
            return file_path

    raise Exception("이미지 생성 결과가 없습니다.")