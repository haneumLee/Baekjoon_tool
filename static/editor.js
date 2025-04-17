// static/editor.js
let editor;
let currentProblemNumber = '';
let currentLanguage = 'python';

require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });

require(['vs/editor/editor.main'], function () {
    editor = monaco.editor.create(document.getElementById('monaco-editor'), {
        value: '# 여기에 코드를 작성하세요',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: {
            enabled: false
        }
    });

    // 언어 변경 이벤트 리스너
    document.getElementById('language-select').addEventListener('change', function(e) {
        currentLanguage = e.target.value;
        monaco.editor.setModelLanguage(editor.getModel(), currentLanguage);
        
        // 기본 템플릿 설정
        if (currentLanguage === 'python') {
            editor.setValue(`def solve():
    # 여기에 코드를 작성하세요
    pass

if __name__ == "__main__":
    solve()`);
        } else if (currentLanguage === 'rust') {
            editor.setValue(`fn main() {
    // 여기에 코드를 작성하세요
}`);
        }
    });
});

async function openDirectoryPicker() {
    try {
        // 브라우저의 디렉토리 선택 API 사용
        const dirHandle = await window.showDirectoryPicker();
        
        // 선택한 폴더 이름으로 전체 경로 구성
        const basePath = '/Users/haneum/Documents/development/baekjoon_tool';
        const completePath = `${basePath}/${dirHandle.name}`;
        document.getElementById('save-directory').value = completePath;
        
        // 서버에 저장 경로 전송
        const formData = new FormData();
        formData.append('directory', completePath);

        const response = await fetch('/set-save-directory', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            alert(data.message);
        } else {
            alert('저장 경로 설정에 실패했습니다: ' + data.message);
        }
    } catch (error) {
        if (error.name === 'SecurityError') {
            alert('디렉토리 접근 권한이 필요합니다.');
        } else {
            alert('오류가 발생했습니다: ' + error);
            console.error('Directory picker error:', error);
        }
    }
}

async function fetchProblem() {
    const problemUrl = document.getElementById('problem-url').value;
    const language = document.getElementById('language-select').value;
    
    if (!problemUrl) {
        alert('문제 URL을 입력해주세요.');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('problem_url', problemUrl);
        formData.append('language', language);

        const response = await fetch('/fetch-problem', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            currentProblemNumber = problemUrl.split('/').pop();
            await loadProblemContent();
            // 입력 예제도 로드
            const inputResponse = await fetch(`/problems/${currentProblemNumber}/input.txt`);
            if (inputResponse.ok) {
                const inputText = await inputResponse.text();
                document.getElementById('input-area').value = inputText;
            }
        } else {
            console.error('Problem fetching error:', data);
            alert('문제를 가져오는데 실패했습니다: ' + data.message);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        alert('오류가 발생했습니다: ' + error);
    }
}

async function loadProblemContent() {
    try {
        const response = await fetch(`/problems/${currentProblemNumber}/README.md`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const content = await response.text();
        document.getElementById('problem-content').innerHTML = marked.parse(content);
    } catch (error) {
        console.error('Problem content loading error:', error);
        document.getElementById('problem-content').innerHTML = '문제 내용을 불러오는데 실패했습니다.';
    }
}

async function runCode() {
    if (!currentProblemNumber) {
        alert('먼저 문제를 가져와주세요.');
        return;
    }

    const formData = new FormData();
    formData.append('problem_number', currentProblemNumber);
    formData.append('language', currentLanguage);

    try {
        const response = await fetch('/run-code', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('output-area').textContent = data.output;
        } else {
            document.getElementById('output-area').textContent = '실행 중 오류 발생: ' + data.message;
        }
    } catch (error) {
        document.getElementById('output-area').textContent = '오류가 발생했습니다: ' + error;
    }
}

async function checkAnswer() {
    if (!currentProblemNumber) {
        alert('먼저 문제를 가져와주세요.');
        return;
    }

    try {
        const outputContent = document.getElementById('output-area').textContent;
        const expectedResponse = await fetch(`/problems/${currentProblemNumber}/expected_output.txt`);
        const expectedOutput = await expectedResponse.text();

        if (outputContent.trim() === expectedOutput.trim()) {
            alert('정답입니다! 🎉');
        } else {
            alert('틀렸습니다. 다시 시도해보세요.');
        }
    } catch (error) {
        alert('정답 확인 중 오류가 발생했습니다: ' + error);
    }
}

async function submitCode() {
    if (!currentProblemNumber) {
        alert('먼저 문제를 가져와주세요.');
        return;
    }

    const code = editor.getValue();
    const submitUrl = `https://www.acmicpc.net/submit/${currentProblemNumber}`;
    
    // 새 창에서 제출 페이지 열기
    const submitWindow = window.open(submitUrl, '_blank');
    
    // 클립보드에 코드 복사
    await navigator.clipboard.writeText(code);
    alert('코드가 클립보드에 복사되었습니다. 제출 페이지에 붙여넣기 해주세요.');
}

async function setSaveDirectory() {
    const directory = document.getElementById('save-directory').value;
    
    if (!directory) {
        alert('저장 경로를 입력해주세요.');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('directory', directory);

        const response = await fetch('/set-save-directory', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (data.status === 'success') {
            alert(data.message);
        } else {
            alert('저장 경로 설정에 실패했습니다: ' + data.message);
        }
    } catch (error) {
        alert('오류가 발생했습니다: ' + error);
    }
}