from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import subprocess
import webbrowser
import uvicorn
import os
import sys
import requests
import cloudscraper
from bs4 import BeautifulSoup
import shutil

app = FastAPI()

# 전역 설정
SETTINGS = {
    "save_directory": "problems"  # 기본 저장 경로
}

# 정적 파일, 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 루트 경로 접속 시 HTML 반환
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/set-save-directory")
async def set_save_directory(directory: str = Form(...)):
    try:
        # 절대 경로로 변환
        abs_path = os.path.abspath(directory)
        # 디렉토리가 없으면 생성
        os.makedirs(abs_path, exist_ok=True)
        SETTINGS["save_directory"] = abs_path
        return {"status": "success", "message": f"저장 경로가 {abs_path}로 설정되었습니다."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/fetch-problem")
async def fetch_problem(problem_url: str = Form(...), language: str = Form(...)):
    try:
        print("\n=== 디버깅 정보 ===")
        
        # URL 정규화
        if 'www.acmicpc.net' in problem_url:
            problem_url = problem_url.replace('www.acmicpc.net', 'acmicpc.net')
        print(f"1. 정규화된 URL: {problem_url}")
        
        # 문제 번호 추출 및 디렉토리 생성
        problem_number = problem_url.split('/')[-1]
        problem_dir = os.path.join(SETTINGS["save_directory"], problem_number)
        os.makedirs(problem_dir, exist_ok=True)
        print(f"2. 문제 디렉토리 생성: {problem_dir}")
        
        # HTTP GET 요청 using cloudscraper
        scraper = cloudscraper.create_scraper()
        response = scraper.get(problem_url)
        print(f"3. HTTP 상태 코드: {response.status_code}")
        
        if response.status_code != 200:
            raise ValueError(f"HTTP 요청 실패: {response.status_code}")
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        print("4. HTML 파싱 완료")
        
        # HTML 구조 확인
        print("\n5. 주요 HTML 요소 확인:")
        print(f"- problem-body div 존재: {soup.select_one('div#problem-body') is not None}")
        print(f"- description section 존재: {soup.select_one('section#description') is not None}")
        print(f"- problem_title span 존재: {soup.select_one('span#problem_title') is not None}")
        print(f"- 페이지 제목: {soup.title.string if soup.title else 'None'}")
        
        print("전체 HTML 구조 디버깅 (상위 1000자):")
        print(response.text[:1000])
        
        # 문제 제목 찾기
        title_element = soup.select_one('#problem_title')
        print(f"6. 제목 요소 찾음: {title_element is not None}")
        
        if not title_element:
            # page-header 내의 h1에서 제목 찾기
            header = soup.select_one('.page-header h1')
            if header:
                # printable 클래스(문제 번호)와 problem-label 클래스(다국어 등 라벨) 제외
                problem_number_element = header.select_one('.printable')
                if problem_number_element:
                    problem_number_text = problem_number_element.text.strip()
                else:
                    problem_number_text = ""
                
                # 라벨 제거
                for label in header.select('.problem-label'):
                    label.decompose()
                
                # 남은 텍스트가 제목
                title = header.text.strip()
                if problem_number_text:
                    title = title.replace(problem_number_text, "").strip()
                problem_title = title
            else:
                problem_title = soup.title.string.strip() if soup.title else "제목을 찾을 수 없음"
        else:
            problem_title = title_element.text.strip()
        
        print(f"7. 찾은 제목: {problem_title}")
        
        # 디버깅용 HTML 출력
        if not title_element and not problem_title:
            print("\n8. HTML 내용 (처음 1000자):")
            print(response.text[:1000])
        
        # 문제 설명, 입력 설명, 출력 설명 찾기
        problem_description = ""
        input_description = ""
        output_description = ""
        
        # problem-body에서 문제 정보 찾기
        problem_body = soup.select_one('div#problem-body')
        if problem_body:
            # description 섹션 찾기
            description_section = problem_body.select_one('section#description')
            if description_section:
                # 문제 설명 찾기
                problem_text = description_section.select_one('div#problem_description')
                if problem_text:
                    problem_description = problem_text.text.strip()
            
            # 입력 섹션 찾기
            input_section = problem_body.select_one('section#input.problem-section')
            if input_section:
                # 헤더 제외
                headline = input_section.select_one('div.headline')
                if headline:
                    headline.decompose()
                
                # 입력 설명 찾기
                input_text = input_section.select_one('div#problem_input.problem-text')
                if input_text:
                    input_description = input_text.text.strip()
                else:
                    # 백업: 전체 섹션 텍스트
                    input_description = input_section.text.strip()
            
            # 출력 섹션 찾기
            output_section = problem_body.select_one('section#output.problem-section')
            if output_section:
                # 헤더 제외
                headline = output_section.select_one('div.headline')
                if headline:
                    headline.decompose()
                
                # 출력 설명 찾기
                output_text = output_section.select_one('div#problem_output.problem-text')
                if output_text:
                    output_description = output_text.text.strip()
                else:
                    # 백업: 전체 섹션 텍스트
                    output_description = output_section.text.strip()
        
        if not problem_description:
            # 기존 방식으로 시도 (섹션 찾기)
            sections = soup.find_all(['section', 'div'], class_=['problem-section', 'section'])
            for section in sections:
                header = section.find(['h2', 'h3'])
                if not header:
                    continue
                
                header_text = header.text.strip()
                content = section.text.replace(header_text, '').strip()
                
                if '문제' in header_text:
                    problem_description = content
                elif '입력' in header_text:
                    input_description = content
                elif '출력' in header_text:
                    output_description = content
        
        if not problem_description:
            print("경고: 문제 설명을 찾을 수 없음. README에는 빈값으로 저장됩니다.")
        
        # 예제 입력/출력 찾기
        sample_inputs = []
        sample_outputs = []
        
        # 1. sampledata 클래스와 ID로 찾기
        sample_inputs = soup.select('pre.sampledata[id^="sample-input"]')
        sample_outputs = soup.select('pre.sampledata[id^="sample-output"]')
        
        if not sample_inputs or not sample_outputs:
            # 2. copy-button의 data-clipboard-target을 통해 찾기
            copy_buttons = soup.select('button.copy-button')
            for button in copy_buttons:
                target = button.get('data-clipboard-target')
                if target:
                    target_element = soup.select_one(target)
                    if target_element:
                        if 'sample-input' in target.lower():
                            sample_inputs.append(target_element)
                        elif 'sample-output' in target.lower():
                            sample_outputs.append(target_element)
        
        print(f"6. 예제 입력 개수: {len(sample_inputs)}")
        print(f"7. 예제 출력 개수: {len(sample_outputs)}")
        
        # Save all sample inputs and outputs
        if sample_inputs and sample_outputs:
            # Save first sample as main test case
            with open(os.path.join(problem_dir, 'input.txt'), 'w', encoding='utf-8') as f:
                f.write(sample_inputs[0].text.strip())
            
            with open(os.path.join(problem_dir, 'expected_output.txt'), 'w', encoding='utf-8') as f:
                f.write(sample_outputs[0].text.strip())
            
            # Save all samples in a separate directory for testing
            samples_dir = os.path.join(problem_dir, 'samples')
            os.makedirs(samples_dir, exist_ok=True)
            
            for i, (sample_input, sample_output) in enumerate(zip(sample_inputs, sample_outputs), 1):
                # Save each sample input
                with open(os.path.join(samples_dir, f'input{i}.txt'), 'w', encoding='utf-8') as f:
                    f.write(sample_input.text.strip())
                
                # Save each sample output
                with open(os.path.join(samples_dir, f'output{i}.txt'), 'w', encoding='utf-8') as f:
                    f.write(sample_output.text.strip())
        
        if not sample_inputs or not sample_outputs:
            print("경고: 예제 입력 또는 출력을 찾을 수 없습니다.")
        
        # Create README.md
        readme_content = f"""# {problem_title}

## 문제
{problem_description}

## 입력
{input_description}

## 출력
{output_description}

## 문제 링크
{problem_url}
"""
        
        with open(os.path.join(problem_dir, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # Create language-specific files
        if language == 'python':
            main_file = 'main.py'
            template = """def solve():
    # 여기에 코드를 작성하세요
    pass

if __name__ == "__main__":
    solve()
"""
        elif language == 'rust':
            main_file = 'main.rs'
            template = """fn main() {
    // 여기에 코드를 작성하세요
}
"""
            # Create Cargo.toml for Rust
            cargo_content = f"""[package]
name = "problem_{problem_number}"
version = "0.1.0"
edition = "2021"
"""
            with open(os.path.join(problem_dir, 'Cargo.toml'), 'w') as f:
                f.write(cargo_content)
        
        # Write main file
        with open(os.path.join(problem_dir, main_file), 'w') as f:
            f.write(template)
        
        return {"status": "success", "message": "Problem files created successfully"}
        
    except ValueError as ve:
        return {"status": "error", "message": str(ve)}
        
    except requests.RequestException as e:
        return {"status": "error", "message": f"Failed to fetch problem: {str(e)}"}
    except Exception as e:
        import traceback
        print("Error details:", traceback.format_exc())
        return {"status": "error", "message": str(e)}

@app.post("/run-code")
async def run_code(problem_number: str = Form(...), language: str = Form(...)):
    try:
        problem_dir = os.path.join('problems', problem_number)
        
        if language == 'python':
            result = subprocess.run(
                ['python', os.path.join(problem_dir, 'main.py')],
                input=open(os.path.join(problem_dir, 'input.txt')).read(),
                capture_output=True,
                text=True
            )
            
            # Save output
            with open(os.path.join(problem_dir, 'output.txt'), 'w') as f:
                f.write(result.stdout)
            
            return {"status": "success", "output": result.stdout}
            
        elif language == 'rust':
            # First compile
            subprocess.run(['cargo', 'build'], cwd=problem_dir)
            
            # Then run
            result = subprocess.run(
                ['cargo', 'run'],
                input=open(os.path.join(problem_dir, 'input.txt')).read(),
                capture_output=True,
                text=True,
                cwd=problem_dir
            )
            
            # Save output
            with open(os.path.join(problem_dir, 'output.txt'), 'w') as f:
                f.write(result.stdout)
            
            return {"status": "success", "output": result.stdout}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 서버 실행 시 자동 브라우저 오픈
if __name__ == "__main__":
    port = 8000
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
