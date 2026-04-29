import os

def save_blog_file(title: str, content: str) -> str:
    os.makedirs("output/blog", exist_ok=True)

    safe_title = title
    safe_title = safe_title.replace("*", "")
    safe_title = safe_title.replace("#", "")
    safe_title = safe_title.replace("[제목]", "")
    safe_title = safe_title.strip()

    for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        safe_title = safe_title.replace(ch, "_")

    safe_title = safe_title[:50].strip()

    if not safe_title:
        safe_title = "blog_post"

    file_path = f"output/blog/{safe_title}.txt"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path