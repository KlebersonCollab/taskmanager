// ==========================================================================
// TaskManager SPA Dashboard Controller (Linear Dark Theme)
// ==========================================================================

const API_BASE = window.location.origin;
let ws = null;
let currentTab = "overview";

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  connectWebSocket();
  refreshCurrentTab();

  // Polling fallback every 6 seconds
  setInterval(() => {
    refreshCurrentTab(true);
  }, 6000);
});

// --- Tab Management ---
function setupTabs() {
  document.querySelectorAll(".nav-tab").forEach(button => {
    button.addEventListener("click", () => {
      const tab = button.getAttribute("data-tab");
      switchTab(tab);
    });
  });
}

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".nav-tab").forEach(b => {
    b.classList.toggle("active", b.getAttribute("data-tab") === tab);
  });
  document.querySelectorAll(".tab-pane").forEach(pane => {
    pane.classList.toggle("active", pane.id === `tab-${tab}`);
  });
  refreshCurrentTab();
}

function refreshCurrentTab(isBackground = false) {
  if (currentTab === "overview") fetchOverview();
  if (currentTab === "workers") fetchWorkers();
  if (currentTab === "queues") fetchTasks();
  if (currentTab === "schedules") fetchSchedules();
  if (currentTab === "dlq") fetchDlq("default");
}

// --- WebSocket Live Stream ---
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/events`;

  const dot = document.getElementById("wsDot");
  const text = document.getElementById("wsText");

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      dot.classList.remove("disconnected");
      text.innerText = "Ao Vivo";
      logEvent("WS", "Conectado ao canal de eventos em tempo real");
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleLiveEvent(payload);
      } catch (err) {
        console.error("Invalid WS message", err);
      }
    };

    ws.onclose = () => {
      dot.classList.add("disconnected");
      text.innerText = "Reconectando...";
      setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  } catch (err) {
    dot.classList.add("disconnected");
    text.innerText = "Desconectado";
  }
}

function handleLiveEvent(evt) {
  const type = evt.type || "EVENT";
  const data = evt.data || {};
  let summary = JSON.stringify(data);

  if (type === "job:enqueued") summary = `Job ${data.job_id?.substring(0, 8)} (${data.task}) enfileirado na fila [${data.queue}]`;
  else if (type === "job:active") summary = `Worker ${data.worker_id?.substring(0, 8)} executando job ${data.job_id?.substring(0, 8)} (${data.task})`;
  else if (type === "job:completed") summary = `Job ${data.job_id?.substring(0, 8)} completado com sucesso (${data.duration?.toFixed(2)}s)`;
  else if (type === "job:failed") summary = `Job ${data.job_id?.substring(0, 8)} FALHOU -> DLQ: ${data.error}`;
  else if (type === "job:retrying") summary = `Job ${data.job_id?.substring(0, 8)} agendado para retry (${data.retry_count}/${data.max_retries})`;
  else if (type === "worker:heartbeat") {
    summary = `Worker ${data.name} [${data.status}] CPU: ${data.cpu_percent}% Mem: ${data.memory_mb}MB`;
    updateWorkerTelemetryCard(data.cpu_percent, data.memory_mb, `${data.name} [${data.status}]`);
  }
  else if (type === "schedule:triggered") summary = `Cron ${data.schedule_id?.substring(0, 8)} disparou job ${data.job_id?.substring(0, 8)}`;

  logEvent(type, summary);

  // Auto refresh overview metrics on significant events
  if (["job:enqueued", "job:active", "job:completed", "job:failed", "schedule:triggered"].includes(type)) {
    if (currentTab === "overview") fetchOverview();
    if (currentTab === "workers") fetchWorkers();
    if (currentTab === "dlq" && type === "job:failed") fetchDlq("default");
  }
}

function updateWorkerTelemetryCard(cpuVal, memMB, detailText) {
  const cpuElem = document.getElementById("m-cpu");
  const cpuBar = document.getElementById("m-cpu-bar");
  const cpuSub = document.getElementById("m-cpu-sub");
  if (cpuElem && cpuBar) {
    cpuElem.innerText = `${Number(cpuVal).toFixed(1)}%`;
    cpuBar.style.width = `${Math.min(100, Math.max(0, Number(cpuVal)))}%`;
    cpuBar.className = "metric-progress-fill" + (cpuVal > 85 ? " danger" : (cpuVal > 70 ? " warn" : ""));
    if (cpuSub && detailText) cpuSub.innerText = detailText;
  }

  const memElem = document.getElementById("m-memory");
  const memBar = document.getElementById("m-memory-bar");
  const memSub = document.getElementById("m-memory-sub");
  if (memElem && memBar) {
    memElem.innerText = `${Number(memMB).toFixed(2)} MB`;
    // Visual bar relative to 256MB per worker
    const visualPct = Math.min(100, (Number(memMB) / 256) * 100);
    memBar.style.width = `${visualPct}%`;
    memBar.className = "metric-progress-fill" + (memMB > 500 ? " danger" : (memMB > 250 ? " warn" : ""));
    if (memSub && detailText) memSub.innerText = detailText;
  }
}

function logEvent(type, msg) {
  const stream = document.getElementById("live-event-stream");
  if (!stream) return;

  const now = new Date().toLocaleTimeString();
  const line = document.createElement("div");
  line.className = "event-line";
  line.innerHTML = `
    <span class="event-time">${now}</span>
    <span class="event-type">${escapeHtml(type)}</span>
    <span class="event-msg">${escapeHtml(msg)}</span>
  `;

  stream.prepend(line);

  // Limit to 50 lines
  while (stream.children.length > 50) {
    stream.removeChild(stream.lastChild);
  }
}

// --- REST API Data Fetchers ---

async function fetchOverview() {
  try {
    const res = await fetch(`${API_BASE}/api/overview`);
    const data = await res.json();

    document.getElementById("m-workers").innerText = data.workers_count;
    document.getElementById("m-workers-sub").innerText = `${data.total_workers} total registrados`;
    document.getElementById("m-active-jobs").innerText = data.active_jobs;
    document.getElementById("m-pending-jobs").innerText = data.total_pending;
    document.getElementById("m-delayed-jobs").innerText = data.total_delayed;
    document.getElementById("m-dlq-jobs").innerText = data.total_dlq;
    document.getElementById("m-schedules").innerText = data.schedules_count;

    // Worker CPU & Memory Telemetry Updates
    const cpuVal = data.worker_cpu_percent !== undefined ? data.worker_cpu_percent : 0;
    const memMB = data.worker_memory_mb !== undefined ? data.worker_memory_mb : 0;
    const detail = data.worker_memory_detail || "Processos worker";
    updateWorkerTelemetryCard(cpuVal, memMB, detail);

    const tbody = document.getElementById("overview-queues-table");
    if (data.queues.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--ink-subtle);">Nenhuma fila ativa.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.queues.map(q => `
      <tr>
        <td><strong>${escapeHtml(q.queue)}</strong></td>
        <td><span class="badge badge-pending">${q.pending}</span></td>
        <td><span class="badge badge-delayed">${q.delayed}</span></td>
        <td><span class="badge badge-failed">${q.dlq}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="switchTab('queues')">Ver Tarefas</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to fetch overview", err);
  }
}

async function fetchWorkers() {
  try {
    const res = await fetch(`${API_BASE}/api/workers`);
    const workers = await res.json();
    const container = document.getElementById("workers-container");

    if (workers.length === 0) {
      container.innerHTML = `<div style="color: var(--ink-subtle);">Nenhum worker ativo encontrado. Inicie um worker com 'taskmanager worker'.</div>`;
      return;
    }

    container.innerHTML = workers.map(w => {
      const isDead = w.status === "dead";
      const badgeClass = isDead ? "badge-failed" : (w.status === "busy" ? "badge-active" : "badge-idle");
      const uptimeSec = Math.round((Date.now() / 1000) - w.started_at);

      return `
        <div class="worker-card">
          <div class="worker-header">
            <div>
              <div class="worker-title">${escapeHtml(w.name)}</div>
              <div style="font-size: 11px; color: var(--ink-tertiary); font-family: var(--font-mono);">${w.id.substring(0, 8)}</div>
            </div>
            <span class="badge ${badgeClass}">${w.status.toUpperCase()}</span>
          </div>
          <div class="worker-stat-row">
            <span>Filas Atendidas</span>
            <strong>${escapeHtml(w.queues.join(", ") || "default")}</strong>
          </div>
          <div class="worker-stat-row">
            <span>Jobs Ativos / Concorrência</span>
            <strong>${w.active_jobs_count} / ${w.concurrency}</strong>
          </div>
          <div class="worker-stat-row">
            <span>Uso de CPU / Memória</span>
            <strong>${w.cpu_percent}% / ${w.memory_mb} MB</strong>
          </div>
          <div class="worker-stat-row">
            <span>Jobs Completados / Falhas</span>
            <strong>${w.completed_jobs_count} / ${w.failed_jobs_count}</strong>
          </div>
          <div class="worker-stat-row">
            <span>Último Heartbeat</span>
            <strong>${timeAgo(w.last_heartbeat)}</strong>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to fetch workers", err);
  }
}

let cachedTasks = [];

async function fetchTasks() {
  try {
    const res = await fetch(`${API_BASE}/api/tasks`);
    cachedTasks = await res.json();
    populateTaskDropdowns(cachedTasks);

    const tbody = document.getElementById("tasks-table");
    if (cachedTasks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--ink-subtle);">Nenhuma tarefa registrada no TaskRegistry.</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedTasks.map(t => `
      <tr>
        <td><strong>${escapeHtml(t.name)}</strong></td>
        <td><code>${escapeHtml(t.queue)}</code></td>
        <td>${t.max_retries}</td>
        <td>${t.retry_backoff}s</td>
        <td>${t.timeout ? `${t.timeout}s` : "Sem limite"}</td>
        <td><span class="badge ${t.is_async ? 'badge-active' : 'badge-pending'}">${t.is_async ? 'Async Coroutine' : 'Sync Function'}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="quickEnqueueTask('${escapeHtml(t.name)}', '${escapeHtml(t.queue)}')">⚡ Enfileirar</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to fetch tasks", err);
  }
}

function populateTaskDropdowns(tasks) {
  const enqSelect = document.getElementById("enq-task-select");
  const schedSelect = document.getElementById("sched-task-select");
  if (!enqSelect || !schedSelect) return;

  const currentEnq = enqSelect.value;
  const currentSched = schedSelect.value;

  const optionsHtml = `
    <optgroup label="⚡ Executores de Script Embutidos">
      <option value="system.run_command">system.run_command (Executar Script / Comando Shell)</option>
      <option value="system.run_script">system.run_script (Executar Script Python .py)</option>
    </optgroup>
    <optgroup label="📦 Tarefas Python Registradas (@task)">
      ${tasks.filter(t => !t.name.startsWith("system.")).map(t => `<option value="${escapeHtml(t.name)}">${escapeHtml(t.name)} (fila: ${escapeHtml(t.queue)})</option>`).join("")}
    </optgroup>
    <optgroup label="⚙️ Customizado">
      <option value="__custom__">Outra tarefa / Nome customizado...</option>
    </optgroup>
  `;

  enqSelect.innerHTML = optionsHtml;
  schedSelect.innerHTML = optionsHtml;

  if (currentEnq) enqSelect.value = currentEnq;
  if (currentSched) schedSelect.value = currentSched;
}

function handleTaskSelectChange(prefix) {
  const select = document.getElementById(`${prefix}-task-select`);
  const customGroup = document.getElementById(`group-${prefix}-custom-task`);
  const queueInput = document.getElementById(`${prefix}-queue`);
  const argsTextarea = document.getElementById(`${prefix}-args`);
  const helpDiv = document.getElementById(`${prefix}-args-help`);
  if (!select) return;

  const taskName = select.value;

  if (taskName === "__custom__") {
    if (customGroup) customGroup.style.display = "block";
    if (argsTextarea) argsTextarea.value = '{\n  "args": [],\n  "kwargs": {}\n}';
    if (helpDiv) helpDiv.innerText = "💡 Informe os argumentos JSON da tarefa customizada.";
    return;
  }

  if (customGroup) customGroup.style.display = "none";

  // Look up task metadata in cachedTasks
  const taskObj = cachedTasks.find(t => t.name === taskName);
  if (taskObj) {
    if (queueInput) queueInput.value = taskObj.queue || "default";

    // Set formatted sample payload with real parameters & types
    const samplePayload = {
      args: [],
      kwargs: taskObj.sample_kwargs || {}
    };
    if (argsTextarea) {
      argsTextarea.value = JSON.stringify(samplePayload, null, 2);
    }

    // Show function signature and docstring helper
    if (helpDiv) {
      const paramsList = (taskObj.parameters || []).map(p => {
        return `${p.name}${p.has_default ? `=${JSON.stringify(p.default)}` : ''}`;
      }).join(", ");
      const doc = taskObj.docstring ? ` — ${taskObj.docstring.split('\n')[0]}` : '';
      helpDiv.innerText = `💡 ${taskName}(${paramsList})${doc}`;
    }
  } else {
    if (argsTextarea && !argsTextarea.value.trim()) {
      argsTextarea.value = '{\n  "args": [],\n  "kwargs": {}\n}';
    }
    if (helpDiv) helpDiv.innerText = "💡 Passe argumentos posicionais ('args') ou nomeados ('kwargs').";
  }
}

async function fetchSchedules() {
  try {
    const res = await fetch(`${API_BASE}/api/schedules`);
    const schedules = await res.json();
    const tbody = document.getElementById("schedules-table");

    if (schedules.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--ink-subtle);">Nenhum cron/agendamento cadastrado. Clique em "+ Novo Cron" para adicionar.</td></tr>`;
      return;
    }

    tbody.innerHTML = schedules.map(s => {
      const expr = s.schedule_type === "cron" ? s.cron_expression : `${s.interval_seconds}s`;
      const nextRunStr = s.next_run ? timeUntil(s.next_run) : "--";
      const statusBadge = s.enabled ? `<span class="badge badge-completed">ATIVO</span>` : `<span class="badge badge-failed">PAUSADO</span>`;

      return `
        <tr>
          <td><strong>${escapeHtml(s.name)}</strong></td>
          <td><code>${escapeHtml(s.task_name)}</code></td>
          <td>${escapeHtml(s.queue)}</td>
          <td><code>${escapeHtml(expr)}</code></td>
          <td>${statusBadge}</td>
          <td>${nextRunStr}</td>
          <td>${s.total_runs}</td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" title="Disparar Agora" onclick="triggerSchedule('${s.id}')">⚡</button>
              <button class="btn btn-secondary btn-sm" onclick="toggleSchedule('${s.id}', ${!s.enabled})">${s.enabled ? 'Pausar' : 'Ativar'}</button>
              <button class="btn btn-danger btn-sm" onclick="deleteSchedule('${s.id}')">Excluir</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to fetch schedules", err);
  }
}

async function fetchDlq(queue = "default") {
  try {
    const res = await fetch(`${API_BASE}/api/dlq/${queue}`);
    const jobs = await res.json();
    const tbody = document.getElementById("dlq-table");

    if (jobs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--ink-subtle);">Nenhum job falho na Dead Letter Queue da fila [${queue}].</td></tr>`;
      return;
    }

    tbody.innerHTML = jobs.map(j => `
      <tr>
        <td><code>${j.id.substring(0, 8)}</code></td>
        <td><strong>${escapeHtml(j.task_name)}</strong></td>
        <td>${escapeHtml(j.queue)}</td>
        <td style="color: var(--semantic-error);">${escapeHtml(j.error || "Erro desconhecido")}</td>
        <td>${j.retry_count} / ${j.max_retries}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary btn-sm" onclick="showJobDetails('${j.id}')">Detalhes</button>
            <button class="btn btn-primary btn-sm" onclick="replayDlqJob('${j.id}')">⚡ Replay</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to fetch DLQ", err);
  }
}

// --- Actions ---

async function triggerSchedule(id) {
  try {
    const res = await fetch(`${API_BASE}/api/schedules/${id}/trigger`, { method: "POST" });
    if (res.ok) {
      alert("Rotina disparada com sucesso!");
      fetchSchedules();
      fetchOverview();
    }
  } catch (err) {
    alert("Erro ao disparar rotina: " + err.message);
  }
}

async function toggleSchedule(id, enabled) {
  try {
    const res = await fetch(`${API_BASE}/api/schedules/${id}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (res.ok) fetchSchedules();
  } catch (err) {
    alert("Erro ao alterar status da rotina: " + err.message);
  }
}

async function deleteSchedule(id) {
  if (!confirm("Deseja realmente excluir este agendamento?")) return;
  try {
    const res = await fetch(`${API_BASE}/api/schedules/${id}`, { method: "DELETE" });
    if (res.ok) fetchSchedules();
  } catch (err) {
    alert("Erro ao excluir agendamento: " + err.message);
  }
}

async function replayDlqJob(jobId) {
  try {
    const res = await fetch(`${API_BASE}/api/dlq/${jobId}/replay`, { method: "POST" });
    if (res.ok) {
      alert("Job reenfileirado para execução!");
      fetchDlq("default");
      fetchOverview();
    }
  } catch (err) {
    alert("Erro ao reenfileirar job: " + err.message);
  }
}

async function purgeDlq(queue = "default") {
  if (!confirm(`Deseja limpar todos os jobs falhos na DLQ da fila [${queue}]?`)) return;
  try {
    const res = await fetch(`${API_BASE}/api/dlq/${queue}/purge`, { method: "POST" });
    if (res.ok) {
      fetchDlq(queue);
      fetchOverview();
    }
  } catch (err) {
    alert("Erro ao limpar DLQ: " + err.message);
  }
}

async function showJobDetails(jobId) {
  try {
    const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
    const job = await res.json();
    document.getElementById("job-detail-title").innerText = `Job ${job.id}`;
    document.getElementById("job-detail-content").innerText = JSON.stringify(job, null, 2);
    openModal("modal-job-detail");
  } catch (err) {
    alert("Erro ao buscar detalhes do job: " + err.message);
  }
}

async function quickEnqueueTask(taskName, queue) {
  if (cachedTasks.length === 0) await fetchTasks();
  openModal("modal-enqueue");
  const select = document.getElementById("enq-task-select");
  if (select) {
    select.value = taskName;
    handleTaskSelectChange("enq");
  }
  if (queue) {
    document.getElementById("enq-queue").value = queue;
  }
}

// --- Modals & Forms ---

function openModal(id) {
  document.getElementById(id).classList.add("show");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("show");
}

async function openEnqueueModal() {
  if (cachedTasks.length === 0) await fetchTasks();
  openModal("modal-enqueue");
  handleTaskSelectChange("enq");
}

async function openScheduleModal() {
  if (cachedTasks.length === 0) await fetchTasks();
  openModal("modal-schedule");
  handleTaskSelectChange("sched");
}

function toggleScheduleTypeFields() {
  const type = document.getElementById("sched-type").value;
  document.getElementById("group-cron").style.display = type === "cron" ? "block" : "none";
  document.getElementById("group-interval").style.display = type === "interval" ? "block" : "none";
}

async function handleEnqueueSubmit(e) {
  e.preventDefault();
  const selectVal = document.getElementById("enq-task-select").value;
  const customVal = document.getElementById("enq-task-name").value.trim();
  const taskName = selectVal === "__custom__" ? customVal : selectVal;

  if (!taskName) {
    alert("Por favor, selecione ou informe o nome da tarefa.");
    return;
  }

  const queue = document.getElementById("enq-queue").value.trim() || "default";
  const delay = parseFloat(document.getElementById("enq-delay").value) || 0;
  const argsRaw = document.getElementById("enq-args").value.trim();

  let parsedArgs = { args: [], kwargs: {} };
  if (argsRaw) {
    try {
      const obj = JSON.parse(argsRaw);
      if (Array.isArray(obj)) parsedArgs.args = obj;
      else if (typeof obj === "object") {
        parsedArgs.args = obj.args || [];
        parsedArgs.kwargs = obj.kwargs || (obj.args === undefined ? obj : {});
      }
    } catch (err) {
      alert("JSON inválido no campo de argumentos.");
      return;
    }
  }

  try {
    const res = await fetch(`${API_BASE}/api/tasks/${taskName}/enqueue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        queue,
        delay,
        args: parsedArgs.args,
        kwargs: parsedArgs.kwargs,
      }),
    });

    if (res.ok) {
      closeModal("modal-enqueue");
      document.getElementById("form-enqueue").reset();
      fetchOverview();
      alert(`Tarefa '${taskName}' enfileirada com sucesso!`);
    } else {
      const errData = await res.json();
      alert("Erro ao enfileirar: " + (errData.detail || "Erro desconhecido"));
    }
  } catch (err) {
    alert("Erro na requisição: " + err.message);
  }
}

async function handleScheduleSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("sched-name").value.trim();
  const selectVal = document.getElementById("sched-task-select").value;
  const customVal = document.getElementById("sched-task").value.trim();
  const taskName = selectVal === "__custom__" ? customVal : selectVal;

  if (!taskName) {
    alert("Por favor, selecione ou informe o nome da tarefa.");
    return;
  }

  const scheduleType = document.getElementById("sched-type").value;
  const queue = document.getElementById("sched-queue").value.trim() || "default";
  const cronExpr = document.getElementById("sched-cron").value.trim();
  const intervalSec = parseFloat(document.getElementById("sched-interval").value) || 0;
  const argsRaw = document.getElementById("sched-args").value.trim();

  let parsedArgs = { args: [], kwargs: {} };
  if (argsRaw) {
    try {
      const obj = JSON.parse(argsRaw);
      if (Array.isArray(obj)) parsedArgs.args = obj;
      else if (typeof obj === "object") {
        parsedArgs.args = obj.args || [];
        parsedArgs.kwargs = obj.kwargs || (obj.args === undefined ? obj : {});
      }
    } catch (err) {
      alert("JSON inválido no campo de argumentos.");
      return;
    }
  }

  const payload = {
    name,
    task_name: taskName,
    queue,
    schedule_type: scheduleType,
    cron_expression: scheduleType === "cron" ? cronExpr : null,
    interval_seconds: scheduleType === "interval" ? intervalSec : null,
    args: parsedArgs.args,
    kwargs: parsedArgs.kwargs,
    enabled: true,
  };

  try {
    const res = await fetch(`${API_BASE}/api/schedules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      closeModal("modal-schedule");
      document.getElementById("form-schedule").reset();
      fetchSchedules();
      fetchOverview();
      alert(`Cron '${name}' cadastrado com sucesso!`);
    } else {
      const errData = await res.json();
      alert("Erro ao criar agendamento: " + (errData.detail || "Erro desconhecido"));
    }
  } catch (err) {
    alert("Erro na requisição: " + err.message);
  }
}

// --- Helpers ---

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function timeAgo(timestamp) {
  if (!timestamp) return "--";
  const diff = Math.max(0, Math.round((Date.now() / 1000) - timestamp));
  if (diff < 5) return "Agora mesmo";
  if (diff < 60) return `Há ${diff}s`;
  if (diff < 3600) return `Há ${Math.floor(diff / 60)} min`;
  return `Há ${Math.floor(diff / 3600)} h`;
}

function timeUntil(timestamp) {
  if (!timestamp) return "--";
  const diff = Math.round(timestamp - (Date.now() / 1000));
  if (diff <= 0) return "Agora";
  if (diff < 60) return `Em ${diff}s`;
  if (diff < 3600) return `Em ${Math.floor(diff / 60)} min`;
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
