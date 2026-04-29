from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from services.prompt_service import load_prompt, update_prompt

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
def admin_page():
    prompt_data = load_prompt()

    return f"""
    <html>
    <body>
        <h2>관리자 페이지</h2>

        <textarea id="prompt" rows="15" cols="100">{prompt_data['blog_prompt']}</textarea>
        <br><br>

        <button onclick="savePrompt()">프롬프트 저장</button>

        <script>
        async function savePrompt() {{
            const prompt = document.getElementById("prompt").value;

            await fetch("/admin/save-prompt", {{
                method: "POST",
                headers: {{"Content-Type": "application/json"}},
                body: JSON.stringify({{blog_prompt: prompt}})
            }});

            alert("저장 완료");
        }}
        </script>
    </body>
    </html>
    """

@router.post("/admin/save-prompt")
def save_prompt(data: dict):
    update_prompt(data)
    return {"message": "저장 완료"}