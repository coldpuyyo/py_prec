import os
import re
from PIL import Image, ImageDraw, ImageFont

def wrap_text(text: str, width: int = 15) -> str:
    lines = []
    while len(text) > width:
        lines.append(text[:width])
        text = text[width:]
    lines.append(text)
    return "\n".join(lines)

def create_cardnews_images(card_text: str) -> list[str]:
    os.makedirs("output", exist_ok=True)

    font_title = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 60)
    font_body = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 40)
    font_small = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 32)

    cards = re.split(r"\[\d+장\]", card_text)
    cards = [card.strip() for card in cards if card.strip()]

    created_files = []

    for index, card in enumerate(cards[:5], start=1):
        title = ""
        body = ""

        for line in card.splitlines():
            if line.startswith("제목:"):
                title = line.replace("제목:", "").strip()
            elif line.startswith("본문:"):
                body = line.replace("본문:", "").strip()

        title = wrap_text(title, 12)
        body = wrap_text(body, 18)

        img = Image.new("RGB", (1080, 1080), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)

        draw.text((80, 100), f"{index}장", fill=(80, 80, 80), font=font_small)
        draw.text((80, 300), title, fill=(20, 20, 20), font=font_title)
        draw.text((80, 500), body, fill=(40, 40, 40), font=font_body)

        file_path = f"output/card_{index}.png"
        img.save(file_path)
        created_files.append(file_path)

    return created_files

def create_thumbnail_image(title: str) -> str:
    os.makedirs("output/thumbnail", exist_ok=True)

    font_title = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 70)
    font_sub = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 38)

    title = wrap_text(title, 10)

    img = Image.new("RGB", (1080, 1080), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    draw.text((80, 220), "중고거래 사기 주의", fill=(255, 255, 255), font=font_sub)
    draw.text((80, 360), title, fill=(255, 255, 255), font=font_title)
    draw.text((80, 860), "피해 사례로 보는 예방 방법", fill=(230, 230, 230), font=font_sub)

    file_path = "output/thumbnail/thumbnail.png"
    img.save(file_path)

    return file_path