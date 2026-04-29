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
        <button onclick="generateCard()">카드뉴스 생성</button>
        <button onclick="generateCardImage()">카드뉴스 이미지 생성</button>
        <button onclick="generateThumbnailText()">썸네일 문구 생성</button>
        <button onclick="generateAIThumbnail()">AI 썸네일 생성</button>
        <!-- <button onclick="generateThumbnailImage()">썸네일 이미지 합성</button> -->
        <button onclick="mergeThumbnail()">썸네일 문구 합성</button>

        <pre id="result"></pre>
        <div id="imageArea"></div>

        <script src="https://js.puter.com/v2/"></script>
        <script>
            let savedThumbnailText = "";
            let savedAIThumbnailImage = null;
            async function generateThumbnailText() {
                const text = document.getElementById("caseText").value;
                document.getElementById("result").innerText = "썸네일 문구 생성 중...";

                const response = await fetch("/thumbnail-text", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({text: text})
                });

                const data = await response.json();
                savedThumbnailText = data.thumbnail_text || "";
                document.getElementById("result").innerText = savedThumbnailText;
            }
            
            async function generateAIThumbnail() {
                const text = document.getElementById("caseText").value;

                document.getElementById("result").innerText = "AI 썸네일 생성 중...";

                const prompt = `
                A high quality blog thumbnail image.

                Scene:
                - A smartphone screen showing a money transfer
                - A warning symbol (red alert icon)
                - A scam situation

                Style:
                - dark background
                - realistic lighting
                - modern UI style
                - cinematic, high contrast
                - clean composition

                Rules:
                - NO text in the image
                - NO random letters
                - NO watermark
                - NO distorted shapes
                - square image (1:1)

                Make it look like a professional YouTube thumbnail background.
                `;

                const image = await puter.ai.txt2img(prompt, false);
                
                savedAIThumbnailImage = image;

                document.getElementById("result").innerText = "";
                document.getElementById("result").appendChild(image);
            }
            
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

            async function generateCard() {
                const text = document.getElementById("caseText").value;
                document.getElementById("result").innerText = "카드뉴스 생성 중...";

                const response = await fetch("/cardnews", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({text: text})
                });

                const data = await response.json();
                document.getElementById("result").innerText =
                    data.cardnews || JSON.stringify(data, null, 2);
            }

            async function generateCardImage() {
                const text = document.getElementById("result").innerText;
                document.getElementById("result").innerText = "카드뉴스 이미지 생성 중...";

                const response = await fetch("/cardnews-image", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({text: text})
                });

                const data = await response.json();
                document.getElementById("result").innerText =
                    JSON.stringify(data, null, 2);
            }
            
            function wrapCanvasText(ctx, text, x, y, maxWidth, lineHeight) {
                let chars = text.split("");
                let line = "";

                for (let i = 0; i < chars.length; i++) {
                    let testLine = line + chars[i];
                    let metrics = ctx.measureText(testLine);

                    if (metrics.width > maxWidth && i > 0) {
                        ctx.fillText(line, x, y);
                        line = chars[i];
                        y += lineHeight;
                    } else {
                        line = testLine;
                    }
                }

                ctx.fillText(line, x, y);
            }
            
            function mergeThumbnail() {
                if (!savedThumbnailText) {
                    alert("먼저 썸네일 문구를 생성하세요.");
                    return;
                }

                if (!savedAIThumbnailImage) {
                    alert("먼저 AI 썸네일 이미지를 생성하세요.");
                    return;
                }

                const canvas = document.createElement("canvas");
                canvas.width = 1080;
                canvas.height = 1080;

                const ctx = canvas.getContext("2d");

                ctx.drawImage(savedAIThumbnailImage, 0, 0, 1080, 1080);

                ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
                ctx.fillRect(60, 620, 960, 300);

                ctx.fillStyle = "white";
                ctx.font = "bold 76px Malgun Gothic, Arial, sans-serif";
                ctx.textAlign = "left";

                wrapCanvasText(ctx, savedThumbnailText, 100, 730, 880, 95);

                ctx.font = "bold 34px Malgun Gothic, Arial, sans-serif";
                ctx.fillStyle = "#eeeeee";
                ctx.fillText("피해 사례로 보는 예방 방법", 100, 880);

                const mergedImage = document.createElement("img");
                mergedImage.src = canvas.toDataURL("image/png");
                mergedImage.style.width = "300px";
                mergedImage.style.display = "block";
                mergedImage.style.marginTop = "20px";

                document.getElementById("imageArea").innerHTML = "";
                document.getElementById("imageArea").appendChild(mergedImage);

                const link = document.createElement("a");
                link.download = "final_thumbnail.png";
                link.href = canvas.toDataURL("image/png");
                link.click();

                document.getElementById("result").innerText = "최종 썸네일 생성 완료\\n문구: " + savedThumbnailText;
            }
        </script>
    </body>
    </html>
    """