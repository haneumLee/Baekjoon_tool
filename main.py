from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import json
import subprocess

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 설정 파일 관련 함수들
def load_settings():
    if os.path.exists('settings.json'):
        with open('settings.json', 'r') as f:
            return json.load(f)
    return {"save_directory": os.path.expanduser("~/baekjoon")}

def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f)

SETTINGS = load_settings()

# 메인 페이지
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "save_directory": SETTINGS["save_directory"]}
    )

# 저장 디렉토리 설정
@app.post("/set-save-directory")
async def set_save_directory(directory: str = Form(...)):
    try:
        # 절대 경로로 변환
        abs_path = os.path.abspath(directory)
        # 디렉토리가 없으면 생성
        os.makedirs(abs_path, exist_ok=True)
        SETTINGS["save_directory"] = abs_path
        save_settings(SETTINGS)
        return {"status": "success", "message": "저장 경로가 설정되었습니다."}
    except Exception as e:
        return {"status": "error", "message": f"저장 경로 설정 실패: {str(e)}"}

# 문제 처리
@app.post("/process-problem")
async def process_problem(
    problem_text: str = Form(...),
    language: str = Form(...),
    problem_number: str = Form(...),
    save_directory: str = Form(...)
):
    try:
        # 문제 텍스트 파싱
        sections = parse_problem_text(problem_text)
        
        # 디렉토리 생성
        problem_dir = os.path.join(save_directory, problem_number)
        os.makedirs(problem_dir, exist_ok=True)

        # README.md 파일 생성
        create_readme(problem_dir, sections)
        
        # 소스 코드 템플릿 생성
        create_source_template(problem_dir, language)
        
        # 예제 입력/출력 파일 생성
        example_input = sections.get("예제 입력 1", "")
        example_output = sections.get("예제 출력 1", "")
        
        if example_input:
            with open(os.path.join(problem_dir, "input.txt"), "w", encoding="utf-8") as f:
                f.write(example_input)
        
        if example_output:
            with open(os.path.join(problem_dir, "output.txt"), "w", encoding="utf-8") as f:
                f.write(example_output)
        
        # 섹션 이름이 포함된 형식으로 문제 텍스트 생성
        formatted_text = format_problem_text(sections)
        
        return {
            "status": "success",
            "message": "문제 파일이 성공적으로 생성되었습니다.",
            "formatted_text": formatted_text,
            "example_input": example_input,
            "example_output": example_output
        }
    except Exception as e:
        return {"status": "error", "message": f"문제 처리 중 오류 발생: {str(e)}"}

def parse_problem_text(text: str) -> dict:
    """문제 텍스트를 파싱하여 섹션별로 분리"""
    sections = {}
    current_section = "제목"
    current_content = []
    
    for line in text.split('\n'):
        line = line.strip()
        # 예제 입력/출력 여러 개 처리
        if line.startswith("예제 입력") or line.startswith("예제 출력"):
            # 이전 섹션 저장
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line
            current_content = []
        elif line in ["문제", "입력", "출력"]:
            # 이전 섹션 저장
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line
            current_content = []
        else:
            current_content.append(line)
    
    # 마지막 섹션 저장
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

def extract_problem_number(title: str) -> str:
    """제목에서 문제 번호 추출"""
    import re
    match = re.search(r'\d+', title)
    return match.group(0) if match else ""

def create_readme(problem_dir: str, sections: dict):
    """README.md 파일 생성"""
    # 기본 섹션 생성
    content_parts = [
        f"# 백준 {sections.get('제목', '')}\n",
        "## 문제 설명",
        f"{sections.get('문제', '')}\n",
        "## 입력 조건",
        f"{sections.get('입력', '')}\n",
        "## 출력 조건",
        f"{sections.get('출력', '')}\n"
    ]
    
    # 예제 입력/출력 쌍 찾기
    example_pairs = []
    example_num = 1
    while True:
        input_key = f"예제 입력 {example_num}"
        output_key = f"예제 출력 {example_num}"
        
        if input_key not in sections or output_key not in sections:
            break
            
        example_pairs.append((
            sections[input_key],
            sections[output_key],
            example_num
        ))
        example_num += 1
    
    # 예제가 있으면 추가
    if example_pairs:
        content_parts.append("## 입력 예제")
        for input_text, _, num in example_pairs:
            content_parts.extend([
                f"[예제 {num}]",
                f"{input_text}\n"
            ])
            
        content_parts.append("## 출력 예제")
        for _, output_text, num in example_pairs:
            content_parts.extend([
                f"[예제 {num}]",
                f"{output_text}\n"
            ])
    
    readme_content = '\n'.join(content_parts)
    
    with open(os.path.join(problem_dir, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme_content)

def create_source_template(problem_dir: str, language: str):
    """언어별 소스 코드 템플릿 생성"""
    if language.lower() == 'python':
        template = '''def solve():
    # 여기에 코드를 작성하세요
    pass

if __name__ == "__main__":
    solve()
'''
        filename = 'main.py'
    
    elif language.lower() == 'rust':
        template = '''fn main() {
    // 여기에 코드를 작성하세요
}
'''
        filename = 'main.rs'
    
    with open(os.path.join(problem_dir, filename), 'w', encoding='utf-8') as f:
        f.write(template)

def format_problem_text(sections: dict) -> str:
    """섹션 이름이 포함된 문제 텍스트 생성"""
    content_parts = []
    
    # 기본 섹션 순서
    basic_sections = ["문제", "입력", "출력"]
    for section in basic_sections:
        if section in sections:
            content_parts.extend([
                f"## {section}",
                sections[section],
                ""  # 빈 줄 추가
            ])
    
    # 예제 입력/출력 쌍 찾기
    example_num = 1
    while True:
        input_key = f"예제 입력 {example_num}"
        output_key = f"예제 출력 {example_num}"
        
        if input_key not in sections or output_key not in sections:
            break
            
        content_parts.extend([
            f"## {input_key}",
            sections[input_key],
            "",
            f"## {output_key}",
            sections[output_key],
            ""
        ])
        example_num += 1
    
    return '\n'.join(content_parts)

# 코드 실행
@app.post("/run-code")
async def run_code(
    problem_dir: str = Form(...),
    language: str = Form(...),
    problem_number: str = Form(...),
    code: str = Form(...)
):
    try:
        # 문제 번호 디렉토리 경로 구성
        full_problem_dir = os.path.join(problem_dir, problem_number)
        
        # 코드를 파일에 저장
        if language.lower() == 'python':
            source_file = os.path.join(full_problem_dir, 'main.py')
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(code)
            cmd = ['python3', 'main.py']
        elif language.lower() == 'rust':
            source_file = os.path.join(full_problem_dir, 'main.rs')
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(code)
            # Rust 코드 컴파일
            compile_cmd = ['rustc', 'main.rs']
            subprocess.run(compile_cmd, cwd=full_problem_dir, check=True)
            cmd = ['./main']
        else:
            return {"status": "error", "message": "지원하지 않는 프로그래밍 언어입니다."}
        
        # 입력 파일 읽기
        input_path = os.path.join(full_problem_dir, 'input.txt')
        with open(input_path, 'r') as f:
            input_data = f.read()
        
        # 코드 실행
        process = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            cwd=full_problem_dir
        )
        
        return {
            "status": "success",
            "message": "코드가 성공적으로 실행되었습니다.",
            "output": process.stdout
        }
    
    except Exception as e:
        return {"status": "error", "message": f"코드 실행 중 오류 발생: {str(e)}"}

@app.post("/create-problem-files")
async def create_problem_files(request: Request):
    try:
        data = await request.json()
        problem_number = data.get("problem_number")
        problem_text = data.get("problem_text")
        example_input = data.get("example_input")
        example_output = data.get("example_output")
        save_directory = data.get("save_directory")

        # 저장 디렉토리 생성
        problem_dir = os.path.join(save_directory, f"problem_{problem_number}")
        os.makedirs(problem_dir, exist_ok=True)

        # README.md 파일 생성
        readme_path = os.path.join(problem_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# 백준 {problem_number}번 문제\n\n")
            f.write(problem_text)

        # 예제 입력 파일 생성
        input_path = os.path.join(problem_dir, "input.txt")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(example_input)

        # 예제 출력 파일 생성
        output_path = os.path.join(problem_dir, "output.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(example_output)

        # 소스 코드 파일 생성
        source_path = os.path.join(problem_dir, f"problem_{problem_number}.py")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(f"""# 백준 {problem_number}번 문제 풀이
import sys
input = sys.stdin.readline

def solve():
    # 여기에 코드를 작성하세요
    pass

if __name__ == "__main__":
    solve()
""")

        return {"status": "success", "message": "파일이 성공적으로 생성되었습니다."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/get-full-path")
async def get_full_path(request: Request):
    try:
        data = await request.json()
        selected_dir = data.get("selected_dir")
        if not selected_dir:
            return {"status": "error", "message": "선택된 디렉토리 정보가 없습니다."}

        # 현재 작업 디렉토리를 기준으로 전체 경로 생성
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트의 디렉토리
        full_path = os.path.abspath(os.path.join(base_dir, selected_dir))
        
        # 디렉토리가 존재하지 않으면 생성
        os.makedirs(full_path, exist_ok=True)
        
        # settings.json 업데이트
        SETTINGS["save_directory"] = full_path
        save_settings(SETTINGS)
        
        return {
            "status": "success",
            "full_path": full_path,
            "message": "디렉토리가 성공적으로 설정되었습니다."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    
    port = 8000
    url = f"http://localhost:{port}"
    webbrowser.open(url)
    uvicorn.run(app, host="0.0.0.0", port=port)
