# main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import subprocess
import webbrowser
import uvicorn
import os

app = FastAPI()

# 정적 파일, 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 루트 경로 접속 시 HTML 반환
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


class RunRequest(BaseModel):
    code: str
    lang: str

@app.post("/run")
async def run_code(req: RunRequest):
    code = req.code
    lang = req.lang
    filename = "main.py" if lang == "py" else "main.rs"

    folder = "temp"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    with open(filepath, "w") as f:
        f.write(code)

    # 실행
    try:
        if lang == "py":
            result = subprocess.run(["python3", filename], cwd=folder, capture_output=True, text=True, timeout=5)
        else:  # rust
            subprocess.run(["rustc", filename], cwd=folder, check=True)
            result = subprocess.run(["./main"], cwd=folder, capture_output=True, text=True, timeout=5)

        output = result.stdout + result.stderr
    except Exception as e:
        output = f"실행 중 오류 발생: {e}"

    return {"output": output}


# 서버 실행 시 자동 브라우저 오픈
if __name__ == "__main__":
    port = 8000
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
