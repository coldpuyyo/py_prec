from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/app", response_class=HTMLResponse)
def app_page():
    return """
    <html>
    <body>
        <h2>피해 사례 자동화 MVP</h2>

        <textarea id="caseText" rows="10" cols="80"></textarea>
        <br><br>

        <button onclick="generateBlog()">블로그 글 생성</button>
        <button onclick="saveBlog()">블로그 글 저장</button>

        <pre id="result"></pre>

        <script>
            async function generateBlog() {
                const text = document.getElementById("caseText").value;
                document.getElementById("result").innerText = "블로그 글 생성 중...";

                const response = await fetch("/blog", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({text: text})
                });

                const data = await response.json();
                document.getElementById("result").innerText =
                    data.blog || JSON.stringify(data, null, 2);
            }

            async function saveBlog() {
                const content = document.getElementById("result").innerText;

                let title = content.split("\\n")[0]
                    .replace("##", "")
                    .replace("#", "")
                    .trim();

                if (!title) {
                    title = "blog_post";
                }

                const response = await fetch("/save-blog", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        title: title,
                        content: content
                    })
                });

                const data = await response.json();
                document.getElementById("result").innerText =
                    content + "\\n\\n[저장 완료]\\n" + data.file;
            }
        </script>
    </body>
    </html>
    """