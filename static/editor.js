// static/editor.js
let editor;

require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.41.0/min/vs' } });
require(['vs/editor/editor.main'], function () {
  editor = monaco.editor.create(document.getElementById('editor'), {
    value: '// 여기에 코드를 작성하세요',
    language: 'python',
    theme: 'vs-dark',
    automaticLayout: true
  });

  document.getElementById('language').addEventListener('change', (e) => {
    monaco.editor.setModelLanguage(editor.getModel(), e.target.value === 'rs' ? 'rust' : 'python');
  });

  document.getElementById('run-button').addEventListener('click', () => {
    const code = editor.getValue();
    const lang = document.getElementById('language').value;

    fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, lang })
    })
    .then(res => res.json())
    .then(data => {
      document.getElementById('output').innerText = data.output;
    });
  });
});