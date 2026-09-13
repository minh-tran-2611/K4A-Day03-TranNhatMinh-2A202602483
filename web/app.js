const query = document.querySelector('#query');
const run = document.querySelector('#run');
const status = document.querySelector('#status');
const llmAnswer = document.querySelector('#llm-answer');
const agentAnswer = document.querySelector('#agent-answer');
const traceBox = document.querySelector('#trace');
const toolCount = document.querySelector('#tool-count');

document.querySelectorAll('[data-query]').forEach(button => button.addEventListener('click', () => {
  query.value = button.dataset.query;
  query.focus();
}));

document.querySelector('#toggle-explain').addEventListener('click', () => {
  const panel = document.querySelector('#explanation');
  panel.hidden = !panel.hidden;
});

const safe = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));

function renderTrace(items) {
  traceBox.innerHTML = items.map(item => {
    const type = item.action_type;
    let detail = item.output || item.thought || '';
    if (type === 'TOOL_EXECUTION') {
      detail = `${item.tool_name}(${JSON.stringify(item.arguments)}) → ${JSON.stringify(item.observation)}`;
    }
    const label = type === 'TOOL_EXECUTION' ? 'ACTION + OBSERVATION' : type.replaceAll('_', ' ');
    return `<div class="trace-item"><span class="step">0${item.step}</span><span class="kind">${safe(label)}</span><p>${safe(detail)}</p></div>`;
  }).join('');
}

const stage = name => document.querySelector(`[data-stage="${name}"]`);

function activate(name) {
  document.querySelectorAll('[data-stage].active').forEach(node => node.classList.remove('active'));
  const node = stage(name);
  if (node) node.classList.add('active');
}

function complete(name) {
  const node = stage(name);
  if (node) node.classList.remove('active'), node.classList.add('done');
}

function resetFlow() {
  document.querySelectorAll('[data-stage], [data-tool]').forEach(node => node.classList.remove('active', 'done', 'selected'));
  llmAnswer.textContent = 'Đang chờ LLM tạo câu trả lời…';
  agentAnswer.textContent = 'Agent chưa bắt đầu xử lý…';
  toolCount.textContent = '0';
  traceBox.innerHTML = '<div class="placeholder">Các sự kiện thật sẽ xuất hiện lần lượt tại đây…</div>';
}

function selectTool(toolName) {
  document.querySelectorAll('[data-tool]').forEach(node => node.classList.remove('selected'));
  document.querySelectorAll(`[data-tool="${toolName}"]`).forEach(node => node.classList.add('selected'));
}

function appendLiveLog(label, detail, step = '•') {
  const placeholder = traceBox.querySelector('.placeholder');
  if (placeholder) placeholder.remove();
  const row = document.createElement('div');
  row.className = 'trace-item live-event';
  row.innerHTML = `<span class="step">${safe(step)}</span><span class="kind">${safe(label)}</span><p>${safe(detail)}</p>`;
  traceBox.appendChild(row);
  row.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}

function handleProgress(data) {
  if (data.event === 'llm_start') {
    status.textContent = 'Agent đã xong · LLM đang tạo câu trả lời đối chiếu…';
  } else if (data.event === 'llm_done') {
    llmAnswer.textContent = data.answer; llmAnswer.classList.remove('empty');
  } else if (data.event === 'agent_start') {
    complete('agent-input'); activate('agent-thought');
    status.textContent = 'Agent đang suy luận bước tiếp theo…';
    appendLiveLog('START', 'Agent đã nhận mục tiêu từ người dùng.', '01');
  } else if (data.event === 'thought') {
    activate('agent-thought');
    agentAnswer.textContent = data.thought;
    appendLiveLog('THOUGHT', data.thought, String(data.step).padStart(2, '0'));
  } else if (data.event === 'tool_selected') {
    complete('agent-thought'); activate('agent-tools'); selectTool(data.tool_name);
    agentAnswer.textContent = `Agent chọn ${data.tool_name} với tham số ${JSON.stringify(data.arguments)}`;
    status.textContent = `Đang thực thi ${data.tool_name}…`;
    appendLiveLog('ACTION', `${data.tool_name}(${JSON.stringify(data.arguments)})`, '→');
  } else if (data.event === 'observation') {
    stage('agent-tools').classList.remove('active');
    document.querySelectorAll('[data-tool].selected').forEach(node => node.classList.add('done'));
    activate('agent-observation');
    status.textContent = `Đã nhận Observation từ ${data.tool_name}`;
    appendLiveLog('OBSERVATION', JSON.stringify(data.observation), '←');
  } else if (data.event === 'final') {
    complete('agent-thought'); complete('agent-observation'); activate('agent-final');
    agentAnswer.textContent = data.answer; agentAnswer.classList.remove('empty');
    appendLiveLog('FINAL ANSWER', data.answer, '✓');
  } else if (data.event === 'agent_done') {
    complete('agent-final');
    toolCount.textContent = data.tool_calls;
    document.querySelector('#agent-time').textContent = `${data.agent_ms} ms`;
    const mode = document.querySelector('#agent-mode');
    mode.textContent = data.agent_live ? 'LIVE GEMINI' : 'MOCK FALLBACK'; mode.className = data.agent_live ? 'live' : 'fallback';
    renderTrace(data.trace);
    status.textContent = `Agent hoàn tất · đang tạo câu trả lời LLM để đối chiếu…`;
  } else if (data.event === 'done') {
    status.textContent = `Hoàn tất · ${data.provider} · ${data.trace_count} bước quan sát`;
  } else if (data.event === 'error') throw new Error(data.message);
}

run.addEventListener('click', async () => {
  if (!query.value.trim()) return query.focus();
  run.disabled = true; resetFlow(); activate('agent-input');
  status.textContent = 'Agent đã nhận mục tiêu…';
  try {
    const response = await fetch('/api/compare-stream', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query:query.value})});
    if (!response.ok || !response.body) throw new Error('Không mở được luồng tiến trình.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    while (true) {
      const {value, done} = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
      const lines = buffer.split('\n'); buffer = lines.pop() || '';
      lines.filter(Boolean).forEach(line => handleProgress(JSON.parse(line)));
      if (done) { if (buffer.trim()) handleProgress(JSON.parse(buffer)); break; }
    }
  } catch (error) {
    status.textContent = error.message;
    document.querySelectorAll('.active').forEach(node => node.classList.remove('active'));
  } finally { run.disabled = false; }
});
