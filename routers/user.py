from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import json

from services.gemini_service import generate_text
from services.prompt_service import load_prompt
from services.scrape_service import scrape_naver_cafe_article

router = APIRouter()

@router.get("/user", response_class=HTMLResponse)
def user_page():
    with open("data/categories.json", "r", encoding="utf-8") as f:
        categories = json.load(f)

    options = "".join([f"<option>{c}</option>" for c in categories])

    return f"""
    <html>
    <body>
        <h2>블로그 원고 생성</h2>

        카테고리:
        <select id="category">{options}</select>
        <br><br>

        <button onclick="scrapeCases()">피해 사례 수집</button>

        <h3>수집된 피해 사례</h3>
        <div id="caseList"></div>

        <input type="hidden" id="selectedUrl">

        <hr>

        상세 요청:
        <textarea id="subInput" rows="5" cols="80"></textarea>
        <br><br>

        소제목:
        <input id="subTitle" style="width:400px;">
        <br><br>

        글자 수:
        <input id="length" value="1200">
        <br><br>

        <button onclick="generate()">원고 생성</button>

        <h3>미리보기</h3>
        <pre id="result" style="white-space: pre-wrap;"></pre>

        <script>
        async function scrapeCases() {{
            const category = document.getElementById("category").value;

            document.getElementById("caseList").innerHTML = "피해 사례 수집 중...";

            const response = await fetch(
                "/scrape/category?category=" + encodeURIComponent(category) + "&limit=10"
            );

            const data = await response.json();

            const list = document.getElementById("caseList");
            list.innerHTML = "";

            if (!data.results || data.results.length === 0) {{
                list.innerHTML = "수집된 글이 없습니다.";
                return;
            }}

            data.results.forEach((item, index) => {{
                const div = document.createElement("div");
                div.style.border = "1px solid #ccc";
                div.style.padding = "10px";
                div.style.margin = "8px 0";
                div.style.cursor = "pointer";

                div.innerText = (index + 1) + ". [" + item.cafe_name + "] " + item.title;

                div.onclick = function() {{
                    document.getElementById("selectedUrl").value = item.url;

                    const allItems = document.querySelectorAll("#caseList div");
                    allItems.forEach(el => el.style.background = "white");

                    div.style.background = "#e8f0ff";
                }};

                list.appendChild(div);
            }});
        }}

        async function generate() {{
            const category = document.getElementById("category").value;
            const url = document.getElementById("selectedUrl").value;
            const subInput = document.getElementById("subInput").value;
            const subTitle = document.getElementById("subTitle").value;
            const length = document.getElementById("length").value;

            if (!url) {{
                alert("먼저 피해 사례를 선택하세요.");
                return;
            }}

            document.getElementById("result").innerText = "원고 생성 중...";

            const response = await fetch("/user/generate", {{
                method: "POST",
                headers: {{"Content-Type": "application/json"}},
                body: JSON.stringify({{
                    category: category,
                    url: url,
                    subInput: subInput,
                    subTitle: subTitle,
                    length: length
                }})
            }});

            const data = await response.json();

            document.getElementById("result").innerText =
                data.result || JSON.stringify(data, null, 2);
        }}
        </script>
    </body>
    </html>
    """
    
@router.post("/user/generate")
def generate_blog(data: dict):
    try:
        prompt_data = load_prompt()

        if data.get("url"):
            article = scrape_naver_cafe_article(data["url"])
            case_text = article["content"]
        else:
            case_text = ""

        prompt = prompt_data["blog_prompt"].format(
            case=case_text,
            sub_input=data.get("subInput", ""),
            sub_title=data.get("subTitle", ""),
            length=data.get("length", "1200")
        )

        result = generate_text(prompt)

        return {
            "result": result
        }

    except Exception as e:
        return {
            "result": f"에러 발생: {str(e)}"
        }