// ==========================================================================
// TaskManager SPA Dashboard Controller (Linear Dark Theme)
// ==========================================================================

const getBasePath = () => {
  const path = window.location.pathname;
  return path.replace(/\/index\.html$/, "").replace(/\/+$/, "");
};
const BASE_PATH = getBasePath();
const API_BASE = window.location.origin + BASE_PATH;
let ws = null;
let currentTab = "overview";

// --- Modern Linear Dark Toast Notification System ---
const toast = {
  show(title, msg = "", type = "info", duration = 4000) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const icons = {
      success: "✅",
      error: "❌",
      warning: "⚠️",
      info: "ℹ️",
    };

    const toastElem = document.createElement("div");
    toastElem.className = `toast toast-${type}`;
    toastElem.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <div class="toast-body">
        <div class="toast-title">${escapeHtml(title)}</div>
        ${msg ? `<div class="toast-msg">${escapeHtml(msg)}</div>` : ""}
      </div>
      <button class="toast-close" onclick="this.closest('.toast').remove()">&times;</button>
    `;

    container.appendChild(toastElem);

    requestAnimationFrame(() => {
      toastElem.classList.add("show");
    });

    if (duration > 0) {
      setTimeout(() => {
        toastElem.classList.remove("show");
        setTimeout(() => toastElem.remove(), 350);
      }, duration);
    }
  },
  success(title, msg) { this.show(title, msg, "success", 4000); },
  error(title, msg) { this.show(title, msg, "error", 5500); },
  warning(title, msg) { this.show(title, msg, "warning", 4500); },
  info(title, msg) { this.show(title, msg, "info", 4000); },
};

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  connectWebSocket();
  refreshCurrentTab();

  // Polling fallback every 3 seconds for continuous live refresh
  setInterval(() => {
    refreshCurrentTab(true);
  }, 3000);
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
  if (currentTab === "dlq") fetchDlq();
  if (currentTab === "history") {
    if (!isBackground) fetchHistory();
    fetchObservabilityMetrics();
    fetchTimeseriesMetrics();
  }
}

// --- WebSocket Live Stream ---
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsPath = `${BASE_PATH}/ws/events`;
  const wsUrl = `${protocol}//${window.location.host}${wsPath}`;

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

  if (type === "job:enqueued") summary = `Job ${data.job_id?.substring(0, 8)} (${data.task || ""}) enfileirado na fila [${data.queue}]`;
  else if (type === "job:delayed") summary = `Job ${data.job_id?.substring(0, 8)} (${data.task || ""}) agendado com delay na fila [${data.queue}]`;
  else if (type === "job:active") summary = `Worker ${data.worker_id?.substring(0, 8)} executando job ${data.job_id?.substring(0, 8)} (${data.task || ""})`;
  else if (type === "job:progress") {
    const pct = data.progress !== undefined ? data.progress : 0;
    const msg = data.message ? ` — ${data.message}` : "";
    summary = `Job ${data.job_id?.substring(0, 8)} (${data.task || ""}) progresso: ${pct}%${msg}`;

    // Live update trace modal if currently open for this job
    if (window._activeTraceJobId === data.job_id) {
      const pctElem = document.getElementById("trace-progress-pct");
      const barElem = document.getElementById("trace-progress-bar");
      const msgElem = document.getElementById("trace-progress-msg");
      if (pctElem) pctElem.innerText = `${pct}%`;
      if (barElem) {
        barElem.style.width = `${pct}%`;
        barElem.className = "progress-bar-fill active";
      }
      if (msgElem && data.message) msgElem.innerText = data.message;
    }
  }
  else if (type === "job:log") {
    summary = `Job ${data.job_id?.substring(0, 8)}: ${data.line || ""}`;

    // Live stream log line into modal if currently open
    if (window._activeTraceJobId === data.job_id && data.line) {
      const logsConsole = document.getElementById("lgtm-logs-console");
      if (logsConsole) {
        const isErr = data.line.includes("[ERROR]") || data.line.includes("[STDERR]") || data.line.includes("Falha");
        const entry = document.createElement("div");
        entry.className = "log-entry";
        entry.innerHTML = `<span class="${isErr ? 'log-err' : 'log-msg'}">${escapeHtml(data.line)}</span>`;
        logsConsole.appendChild(entry);
        logsConsole.scrollTop = logsConsole.scrollHeight;
      }
    }
  }
  else if (type === "job:completed") {
    const durMs = data.duration !== undefined && data.duration !== null ? data.duration * 1000 : null;
    const durFormatted = durMs !== null ? formatDuration(durMs) : "0.00s";
    summary = `Job ${data.job_id?.substring(0, 8)} completado com sucesso (${durFormatted})`;

    if (window._activeTraceJobId === data.job_id) {
      const pctElem = document.getElementById("trace-progress-pct");
      const barElem = document.getElementById("trace-progress-bar");
      const msgElem = document.getElementById("trace-progress-msg");
      if (pctElem) pctElem.innerText = "100%";
      if (barElem) {
        barElem.style.width = "100%";
        barElem.className = "progress-bar-fill completed";
      }
      if (msgElem) msgElem.innerText = "Concluído com sucesso";
    }
  }
  else if (type === "job:failed") summary = `Job ${data.job_id?.substring(0, 8)} FALHOU -> DLQ [${data.queue}]: ${data.error || "Erro"}`;
  else if (type === "job:retrying") summary = `Job ${data.job_id?.substring(0, 8)} agendado para retry (${data.retry_count}/${data.max_retries})`;
  else if (type === "job:cancelled") summary = `Job ${data.job_id?.substring(0, 8)} cancelado na fila [${data.queue}]`;
  else if (type === "job:replayed") summary = `Job ${data.job_id?.substring(0, 8)} reenfileirado da DLQ para a fila [${data.queue}]`;
  else if (type === "worker:heartbeat") {
    summary = `Worker ${data.name} [${data.status}] CPU: ${data.cpu_percent}% Mem: ${data.memory_mb}MB`;
    updateWorkerTelemetryCard(data.cpu_percent, data.memory_mb, `${data.name} [${data.status}]`);
  }
  else if (type === "schedule:triggered") summary = `Cron ${data.schedule_id?.substring(0, 8)} disparou job ${data.job_id?.substring(0, 8)}`;
  else if (type === "schedule:created" || type === "schedule:updated" || type === "schedule:deleted") summary = `Rotina agendada atualizada: ${type}`;
  else if (type === "worker:spawned" || type === "worker:stopped") summary = `Worker status alterado: ${type}`;

  logEvent(type, summary);

  // Instantly refresh current tab state in real time for any relevant event
  if (currentTab === "overview") fetchOverview();
  if (currentTab === "workers") fetchWorkers();
  if (currentTab === "schedules" && type.startsWith("schedule:")) fetchSchedules();
  if (currentTab === "dlq" && (type === "job:failed" || type === "job:replayed")) fetchDlq();
  if (currentTab === "history" && type.startsWith("job:")) {
    fetchHistory();
    fetchObservabilityMetrics();
  }
}

function updateWorkerTelemetryCard(cpuVal, memMB, detailText) {
  const cpuElem = document.getElementById("m-cpu");
  const cpuBar = document.getElementById("m-cpu-bar");
  const cpuSub = document.getElementById("m-cpu-sub");
  if (cpuElem && cpuBar) {
    const numCpu = Number(cpuVal) || 0;
    cpuElem.innerText = `${numCpu.toFixed(1)}%`;
    cpuBar.style.width = `${Math.min(100, Math.max(0, numCpu))}%`;
    cpuBar.className = "metric-progress-fill" + (numCpu > 85 ? " danger" : (numCpu > 70 ? " warn" : ""));
    if (cpuSub && detailText) cpuSub.innerText = detailText;
  }

  const memElem = document.getElementById("m-memory");
  const memBar = document.getElementById("m-memory-bar");
  const memSub = document.getElementById("m-memory-sub");
  if (memElem && memBar) {
    const numMem = Number(memMB) || 0;
    memElem.innerText = `${numMem.toFixed(1)} MB`;
    // Visual bar relative to 256MB per worker
    const visualPct = Math.min(100, (numMem / 256) * 100);
    memBar.style.width = `${visualPct}%`;
    memBar.className = "metric-progress-fill" + (numMem > 500 ? " danger" : (numMem > 250 ? " warn" : ""));
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

    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val !== undefined && val !== null ? val : 0;
    };

    setText("m-workers", data.workers_count);
    const workersSub = document.getElementById("m-workers-sub");
    if (workersSub) workersSub.innerText = `${data.total_workers || data.workers_count || 0} total registrados`;

    setText("m-active-jobs", data.active_jobs);
    setText("m-pending-jobs", data.total_pending);
    setText("m-delayed-jobs", data.total_delayed);
    setText("m-dlq-jobs", data.total_dlq);
    setText("m-schedules", data.schedules_count);

    // Worker CPU & Memory Telemetry Updates
    const cpuVal = data.worker_cpu_percent !== undefined ? data.worker_cpu_percent : 0;
    const memMB = data.worker_memory_mb !== undefined ? data.worker_memory_mb : 0;
    const detail = data.worker_memory_detail || "Processos worker";
    updateWorkerTelemetryCard(cpuVal, memMB, detail);

    const tbody = document.getElementById("overview-queues-table");
    if (!tbody) return;
    if (!data.queues || data.queues.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--ink-subtle);">Nenhuma fila ativa.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.queues.map(q => `
      <tr>
        <td><strong>${escapeHtml(q.queue)}</strong></td>
        <td><span class="badge ${q.pending > 0 ? "badge-active" : "badge-pending"}">${q.pending}</span></td>
        <td><span class="badge ${q.delayed > 0 ? "badge-delayed" : "badge-pending"}">${q.delayed}</span></td>
        <td><span class="badge ${q.dlq > 0 ? "badge-failed" : "badge-pending"}">${q.dlq}</span></td>
        <td>
          <div class="action-group">
            <button class="btn-action" title="Enfileirar Tarefa" onclick="quickEnqueueTask('', '${escapeHtml(q.queue)}')">⚡ Enfileirar</button>
            <button class="btn-action" title="Ver Tarefas" onclick="switchTab('queues')">Ver Tarefas</button>
            ${q.queue !== 'default' && q.pending === 0 && q.delayed === 0 && q.dlq === 0 ? `<button class="btn-action btn-action-danger" title="Excluir Fila Vazia" onclick="deleteQueue('${escapeHtml(q.queue)}')">🗑</button>` : ''}
          </div>
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
    const countBadge = document.getElementById("workers-count-badge");

    if (countBadge) countBadge.innerText = `${workers.length} workers`;

    if (!container) return;
    if (workers.length === 0) {
      container.innerHTML = `<div style="color: var(--ink-subtle);">Nenhum worker ativo encontrado. Clique em <strong>+ Criar ▾ ➔ Iniciar Novo Worker</strong> acima ou execute <code>taskmanager worker</code> no terminal.</div>`;
      return;
    }

    container.innerHTML = workers.map(w => {
      const isDead = w.status === "dead";
      let badgeClass = "badge-idle";
      if (isDead) badgeClass = "badge-failed";
      else if (w.status === "busy") badgeClass = "badge-active";
      else if (w.status === "paused" || w.status === "throttled") badgeClass = "badge-delayed";

      const pauseBtn = w.status === "paused"
        ? `<button class="btn-action" onclick="resumeWorker('${w.id}')">▶ Retomar</button>`
        : `<button class="btn-action" onclick="pauseWorker('${w.id}')">⏸ Pausar</button>`;

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
            <span>Jobs Concluídos / Falhas</span>
            <strong>${w.completed_jobs_count} / ${w.failed_jobs_count}</strong>
          </div>
          <div class="worker-stat-row">
            <span>Último Heartbeat</span>
            <strong>${timeAgo(w.last_heartbeat)}</strong>
          </div>
          <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--hairline); display: flex; gap: 6px; justify-content: flex-end;">
            ${pauseBtn}
            <button class="btn-action btn-action-danger" onclick="stopWorker('${w.id}')">⏹ Parar</button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to fetch workers", err);
  }
}

function openSpawnWorkerModal() {
  const nameInput = document.getElementById("spawn-worker-name");
  if (nameInput) {
    nameInput.value = `worker-ui-${Math.random().toString(36).substring(2, 6)}`;
  }
  openModal("modal-spawn-worker");
}

async function handleSpawnWorkerSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("spawn-worker-name")?.value.trim() || undefined;
  const queuesRaw = document.getElementById("spawn-worker-queues")?.value.trim() || "default";
  const queues = queuesRaw.split(",").map(q => q.trim()).filter(Boolean);
  const concurrency = parseInt(document.getElementById("spawn-worker-concurrency")?.value || "5", 10);
  const maxMemRaw = document.getElementById("spawn-worker-max-mem")?.value.trim();
  const maxCpuRaw = document.getElementById("spawn-worker-max-cpu")?.value.trim();

  const payload = {
    name,
    queues,
    concurrency,
    max_memory_mb: maxMemRaw ? parseFloat(maxMemRaw) : null,
    max_cpu_percent: maxCpuRaw ? parseFloat(maxCpuRaw) : null,
  };

  try {
    const res = await fetch(`${API_BASE}/api/workers/spawn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      closeModal("modal-spawn-worker");
      fetchWorkers();
      fetchOverview();
      logEvent("WORKER", `Novo worker '${name || 'dinâmico'}' iniciado com sucesso.`);
      toast.success("Worker iniciado", `Worker '${name || 'dinâmico'}' está ativo e escutando [${queues.join(', ')}].`);
    } else {
      let errMsg = "Erro desconhecido";
      try {
        const errData = await res.json();
        errMsg = errData.detail || errData.message || JSON.stringify(errData);
      } catch {
        errMsg = await res.text();
      }
      toast.error("Erro ao iniciar worker", errMsg);
    }
  } catch (err) {
    toast.error("Falha na requisição", err.message);
  }
}

async function pauseWorker(workerId) {
  try {
    const res = await fetch(`${API_BASE}/api/workers/${workerId}/pause`, { method: "POST" });
    if (res.ok) {
      fetchWorkers();
      logEvent("CONTROL", `Worker ${workerId.substring(0, 8)} pausado.`);
      toast.warning("Worker pausado", `O worker ${workerId.substring(0, 8)} pausou o consumo de tarefas.`);
    }
  } catch (err) {
    toast.error("Erro ao pausar worker", err.message);
  }
}

async function resumeWorker(workerId) {
  try {
    const res = await fetch(`${API_BASE}/api/workers/${workerId}/resume`, { method: "POST" });
    if (res.ok) {
      fetchWorkers();
      logEvent("CONTROL", `Worker ${workerId.substring(0, 8)} retomado.`);
      toast.success("Worker retomado", `O worker ${workerId.substring(0, 8)} voltou a processar tarefas.`);
    }
  } catch (err) {
    toast.error("Erro ao retomar worker", err.message);
  }
}

async function stopWorker(workerId) {
  try {
    const res = await fetch(`${API_BASE}/api/workers/${workerId}/stop`, { method: "POST" });
    if (res.ok) {
      fetchWorkers();
      logEvent("CONTROL", `Worker ${workerId.substring(0, 8)} encerrado.`);
      toast.info("Worker encerrado", `O worker ${workerId.substring(0, 8)} foi finalizado com sucesso.`);
    }
  } catch (err) {
    toast.error("Erro ao parar worker", err.message);
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
          <div class="action-group">
            <button class="btn-action" title="Disparar Tarefa Imediata" onclick="quickEnqueueTask('${escapeHtml(t.name)}', '${escapeHtml(t.queue)}')">⚡ Enfileirar</button>
            <button class="btn-action" title="Configurar Cron ou Intervalo" onclick="quickScheduleTask('${escapeHtml(t.name)}', '${escapeHtml(t.queue)}')">⏰ Agendar</button>
          </div>
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
            <div class="action-group">
              <button class="btn-action" title="Disparar Agora" onclick="triggerSchedule('${s.id}')">⚡ Executar</button>
              <button class="btn-action" title="${s.enabled ? 'Pausar' : 'Ativar'}" onclick="toggleSchedule('${s.id}', ${!s.enabled})">${s.enabled ? '⏸ Pausar' : '▶ Ativar'}</button>
              <button class="btn-action btn-action-danger" title="Excluir Agendamento" onclick="deleteSchedule('${s.id}')">🗑</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to fetch schedules", err);
  }
}

async function fetchDlq(selectedQueue = null) {
  try {
    const filterSelect = document.getElementById("dlq-filter-queue");
    const queue = selectedQueue || (filterSelect ? filterSelect.value : "all") || "all";
    const res = await fetch(`${API_BASE}/api/dlq/${queue}`);
    const jobs = await res.json();
    const tbody = document.getElementById("dlq-table");
    const countBadge = document.getElementById("dlq-count-badge");

    if (countBadge) {
      countBadge.innerText = `${jobs.length} falha${jobs.length !== 1 ? 's' : ''}`;
    }

    // Populate queue filter dropdown with active queues
    if (filterSelect && filterSelect.dataset.populated !== "true") {
      try {
        const queuesRes = await fetch(`${API_BASE}/api/queues`);
        if (queuesRes.ok) {
          const queues = await queuesRes.json();
          const currentVal = filterSelect.value || "all";
          const optionsHtml = `<option value="all">Todas as Filas</option>` +
            queues.map(q => `<option value="${escapeHtml(q.queue)}">${escapeHtml(q.queue)} (${q.dlq})</option>`).join("");
          filterSelect.innerHTML = optionsHtml;
          filterSelect.value = currentVal;
        }
      } catch {
        // Soft fail
      }
    }

    if (!tbody) return;
    if (jobs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--ink-subtle);">Nenhum job falho na Dead Letter Queue ${queue === 'all' ? 'em nenhuma fila' : `da fila [${queue}]`}.</td></tr>`;
      return;
    }

    tbody.innerHTML = jobs.map(j => `
      <tr>
        <td><code>${j.id.substring(0, 8)}</code></td>
        <td><strong>${escapeHtml(j.task_name)}</strong></td>
        <td><code>${escapeHtml(j.queue)}</code></td>
        <td style="color: var(--semantic-error);">${escapeHtml(j.error || "Erro desconhecido")}</td>
        <td>${j.retry_count} / ${j.max_retries}</td>
        <td>
          <div class="action-group">
            <button class="btn-action" title="Ver Detalhes do Erro" onclick="showJobDetails('${j.id}')">🔍 Detalhes</button>
            <button class="btn-action" title="Reenfileirar Job na Fila" onclick="replayDlqJob('${j.id}')">⚡ Replay</button>
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
      toast.success("Rotina disparada", "Tarefa colocada na fila para execução imediata.");
      fetchSchedules();
      fetchOverview();
    } else {
      const err = await res.json();
      toast.error("Erro ao disparar rotina", err.detail || "Falha na execução");
    }
  } catch (err) {
    toast.error("Erro ao disparar rotina", err.message);
  }
}

async function toggleSchedule(id, enabled) {
  try {
    const res = await fetch(`${API_BASE}/api/schedules/${id}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (res.ok) {
      toast.info(enabled ? "Rotina ativada" : "Rotina pausada", "Status do agendamento atualizado.");
      fetchSchedules();
    }
  } catch (err) {
    toast.error("Erro ao alterar rotina", err.message);
  }
}

async function deleteSchedule(id) {
  try {
    const res = await fetch(`${API_BASE}/api/schedules/${id}`, { method: "DELETE" });
    if (res.ok) {
      toast.info("Rotina excluída", "Agendamento removido com sucesso.");
      fetchSchedules();
    }
  } catch (err) {
    toast.error("Erro ao excluir agendamento", err.message);
  }
}

async function replayDlqJob(jobId) {
  try {
    const res = await fetch(`${API_BASE}/api/dlq/${jobId}/replay`, { method: "POST" });
    if (res.ok) {
      toast.success("Job reenfileirado", "Job reenviado para reprocessamento na fila.");
      fetchDlq();
      fetchOverview();
    }
  } catch (err) {
    toast.error("Erro ao reenfileirar job", err.message);
  }
}

async function handlePurgeDlq() {
  const filterSelect = document.getElementById("dlq-filter-queue");
  const queue = (filterSelect ? filterSelect.value : "all") || "all";
  await purgeDlq(queue);
}

async function purgeDlq(queue = "all") {
  try {
    const res = await fetch(`${API_BASE}/api/dlq/${queue}/purge`, { method: "POST" });
    if (res.ok) {
      toast.info("DLQ limpa", `Jobs falhos ${queue === 'all' ? 'de todas as filas' : `na fila [${queue}]`} foram removidos.`);
      fetchDlq(queue);
      fetchOverview();
    }
  } catch (err) {
    toast.error("Erro ao limpar DLQ", err.message);
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
    toast.error("Erro ao buscar detalhes", err.message);
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

async function quickScheduleTask(taskName, queue) {
  if (cachedTasks.length === 0) await fetchTasks();
  openScheduleModal(taskName);
  if (queue) {
    const qInput = document.getElementById("sched-queue");
    if (qInput) qInput.value = queue;
  }
}

async function openScheduleModal(taskName = null) {
  if (cachedTasks.length === 0) await fetchTasks();
  const nameInput = document.getElementById("sched-name");
  const select = document.getElementById("sched-task-select");
  const cronInput = document.getElementById("sched-cron");
  const intervalInput = document.getElementById("sched-interval");

  if (cronInput && !cronInput.value) cronInput.value = "*/5 * * * *";
  if (intervalInput && !intervalInput.value) intervalInput.value = "60";

  openModal("modal-schedule");
  if (taskName && select) {
    select.value = taskName;
    if (nameInput) {
      nameInput.value = `Rotina - ${taskName}`;
    }
  }
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
    toast.warning("Selecione uma tarefa", "Por favor, selecione ou informe o nome da tarefa.");
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
      toast.error("JSON Inválido", "Verifique a formatação dos argumentos JSON da tarefa.");
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
      toast.success("Tarefa enfileirada", `Job '${taskName}' enviado para a fila [${queue}].`);
    } else {
      let errMsg = "Erro desconhecido";
      try {
        const errData = await res.json();
        errMsg = errData.detail || errData.message || JSON.stringify(errData);
      } catch {
        errMsg = await res.text();
      }
      toast.error("Erro ao enfileirar", errMsg);
    }
  } catch (err) {
    toast.error("Falha na requisição", err.message);
  }
}

async function handleScheduleSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("sched-name").value.trim();
  const selectVal = document.getElementById("sched-task-select").value;
  const customVal = document.getElementById("sched-task").value.trim();
  const taskName = selectVal === "__custom__" ? customVal : selectVal;

  if (!taskName) {
    toast.warning("Selecione uma tarefa", "Por favor, selecione ou informe o nome da tarefa.");
    return;
  }

  const scheduleType = document.getElementById("sched-type").value;
  const queue = document.getElementById("sched-queue").value.trim() || "default";
  let cronExpr = document.getElementById("sched-cron").value.trim();
  const intervalSec = parseFloat(document.getElementById("sched-interval").value) || 60;
  const argsRaw = document.getElementById("sched-args").value.trim();

  if (scheduleType === "cron" && !cronExpr) {
    cronExpr = "*/5 * * * *";
  }

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
      toast.error("JSON Inválido", "Verifique a formatação dos argumentos JSON da rotina.");
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
      toast.success("Cron cadastrado", `Rotina '${name}' configurada com sucesso.`);
    } else {
      let errMsg = "Erro desconhecido";
      try {
        const errData = await res.json();
        errMsg = errData.detail || errData.message || JSON.stringify(errData);
      } catch {
        errMsg = await res.text();
      }
      toast.error("Erro ao criar agendamento", errMsg);
    }
  } catch (err) {
    toast.error("Falha na requisição", err.message);
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

function formatDuration(ms, options = {}) {
  if (ms === null || ms === undefined || isNaN(ms)) return options.fallback || "--";
  const num = Number(ms);
  if (num <= 0) return "0.0 ms";

  const { includeExact = false } = options;

  if (num < 1000) {
    return `${num.toFixed(1)} ms`;
  }

  const totalSec = num / 1000;
  const exactStr = includeExact ? ` (${num.toFixed(1)}ms)` : "";

  if (num < 60000) {
    return `${totalSec.toFixed(2)}s${exactStr}`;
  }

  if (num < 3600000) {
    const mins = Math.floor(totalSec / 60);
    const remSec = (totalSec % 60).toFixed(1);
    const secStr = Number(remSec) < 10 ? `0${remSec}` : remSec;
    return `${mins}m ${secStr}s${exactStr}`;
  }

  const hours = Math.floor(totalSec / 3600);
  const remMins = Math.floor((totalSec % 3600) / 60);
  const remSec = Math.floor(totalSec % 60);
  const minStr = remMins < 10 ? `0${remMins}` : remMins;
  const secStr = remSec < 10 ? `0${remSec}` : remSec;
  return `${hours}h ${minStr}m ${secStr}s${exactStr}`;
}

// --- LGTM Observability & Execution History ---

let historySearchTimer = null;
function debounceFetchHistory() {
  clearTimeout(historySearchTimer);
  historySearchTimer = setTimeout(fetchHistory, 300);
}

async function fetchObservabilityMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/metrics/observability`);
    const m = await res.json();

    const rateElem = document.getElementById("obs-success-rate");
    const rateBar = document.getElementById("obs-success-bar");
    const rateSub = document.getElementById("obs-success-sub");
    if (rateElem && rateBar) {
      const rate = m.success_rate_percent !== undefined ? m.success_rate_percent : 100;
      rateElem.innerText = `${rate.toFixed(1)}%`;
      rateBar.style.width = `${rate}%`;
      rateBar.className = "metric-progress-fill" + (rate < 80 ? " danger" : (rate < 95 ? " warn" : ""));
      if (rateSub) rateSub.innerText = `${m.failed_count || 0} falhas de ${m.total_executions || 0} total`;
    }

    const avgMs = m.avg_duration_ms !== undefined && m.avg_duration_ms !== null ? Number(m.avg_duration_ms) : 0;
    const avgElem = document.getElementById("obs-avg-duration");
    const avgSub = document.getElementById("obs-avg-duration-sub");
    if (avgElem) {
      avgElem.innerText = formatDuration(avgMs);
      if (avgSub) {
        avgSub.innerText = avgMs >= 1000 ? `${avgMs.toFixed(1)} ms — Média de execução` : "Tempo médio de execução";
      }
    }

    const p95Ms = m.p95_duration_ms !== undefined && m.p95_duration_ms !== null ? Number(m.p95_duration_ms) : 0;
    const p95Elem = document.getElementById("obs-p95-duration");
    const p95Sub = document.getElementById("obs-p95-duration-sub");
    if (p95Elem) {
      p95Elem.innerText = formatDuration(p95Ms);
      if (p95Sub) {
        p95Sub.innerText = p95Ms >= 1000 ? `${p95Ms.toFixed(1)} ms — 95% das execuções` : "95% das execuções abaixo";
      }
    }

    const tpElem = document.getElementById("obs-throughput");
    if (tpElem) tpElem.innerText = `${m.throughput_per_minute || 0} / min`;
  } catch (err) {
    console.error("Failed to fetch observability metrics", err);
  }
}

let currentObsTimeWindow = 30;
let cachedTimeseriesData = null;

function setTimeWindow(minutes) {
  currentObsTimeWindow = Number(minutes);
  document.querySelectorAll(".time-window-pill").forEach(pill => {
    pill.classList.toggle("active", Number(pill.getAttribute("data-window")) === currentObsTimeWindow);
  });
  fetchTimeseriesMetrics();
}

async function fetchTimeseriesMetrics() {
  try {
    const res = await fetch(`${API_BASE}/api/metrics/timeseries?window_minutes=${currentObsTimeWindow}`);
    if (!res.ok) return;
    const data = await res.json();
    cachedTimeseriesData = data;

    renderLatencyHistogram(data.latency_histogram, data.latency_percentiles);
    renderThroughputCanvas(data.throughput_series);
  } catch (err) {
    console.error("Failed to fetch timeseries metrics", err);
  }
}

function renderLatencyHistogram(histogram, percentiles) {
  if (percentiles) {
    const p50Elem = document.getElementById("hist-p50");
    const p90Elem = document.getElementById("hist-p90");
    const p95Elem = document.getElementById("hist-p95");
    const p99Elem = document.getElementById("hist-p99");
    if (p50Elem) p50Elem.innerText = `${percentiles.p50_ms || 0}ms`;
    if (p90Elem) p90Elem.innerText = `${percentiles.p90_ms || 0}ms`;
    if (p95Elem) p95Elem.innerText = `${percentiles.p95_ms || 0}ms`;
    if (p99Elem) p99Elem.innerText = `${percentiles.p99_ms || 0}ms`;
  }

  const container = document.getElementById("latency-histogram-bars");
  if (!container) return;
  if (!histogram || histogram.length === 0) {
    container.innerHTML = `<div style="color: var(--ink-subtle); font-size: 11px; text-align: center;">Sem dados de latência</div>`;
    return;
  }

  container.innerHTML = histogram.map(h => `
    <div class="histogram-row">
      <div class="histogram-label">${escapeHtml(h.bucket)}</div>
      <div class="histogram-bar-track">
        <div class="histogram-bar-fill" style="width: ${h.percentage}%;"></div>
      </div>
      <div class="histogram-val">${h.count} (${h.percentage}%)</div>
    </div>
  `).join("");
}

function renderThroughputCanvas(series) {
  const canvas = document.getElementById("throughput-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const rect = canvas.getBoundingClientRect();
  const width = rect.width || canvas.parentElement.clientWidth || 400;
  const height = 180;
  const dpr = window.devicePixelRatio || 1;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, width, height);

  if (!series || series.length === 0) {
    ctx.fillStyle = "rgba(255, 255, 255, 0.3)";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Sem execuções no período", width / 2, height / 2);
    return;
  }

  const paddingLeft = 30;
  const paddingRight = 10;
  const paddingTop = 15;
  const paddingBottom = 25;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  let maxVal = 1;
  series.forEach(pt => {
    if (pt.total > maxVal) maxVal = pt.total;
  });
  maxVal = Math.max(4, Math.ceil(maxVal * 1.25));

  // Draw grid lines
  const gridSteps = 3;
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
  ctx.fillStyle = "rgba(255, 255, 255, 0.3)";
  ctx.font = "10px monospace";
  ctx.textAlign = "right";

  for (let i = 0; i <= gridSteps; i++) {
    const y = paddingTop + (chartHeight / gridSteps) * (gridSteps - i);
    const val = Math.round((maxVal / gridSteps) * i);

    ctx.beginPath();
    ctx.moveTo(paddingLeft, y);
    ctx.lineTo(width - paddingRight, y);
    ctx.stroke();

    ctx.fillText(`${val}`, paddingLeft - 6, y + 3);
  }

  const n = series.length;
  const getX = (idx) => paddingLeft + (chartWidth / Math.max(1, n - 1)) * idx;
  const getY = (val) => paddingTop + chartHeight - (val / maxVal) * chartHeight;

  // 1. Draw Completed Area & Line (#5e6ad2)
  ctx.beginPath();
  ctx.moveTo(getX(0), getY(0));
  series.forEach((pt, idx) => {
    ctx.lineTo(getX(idx), getY(pt.completed));
  });
  ctx.lineTo(getX(n - 1), getY(0));
  ctx.closePath();
  const gradCompleted = ctx.createLinearGradient(0, paddingTop, 0, paddingTop + chartHeight);
  gradCompleted.addColorStop(0, "rgba(94, 106, 210, 0.25)");
  gradCompleted.addColorStop(1, "rgba(94, 106, 210, 0.0)");
  ctx.fillStyle = gradCompleted;
  ctx.fill();

  ctx.beginPath();
  series.forEach((pt, idx) => {
    const x = getX(idx);
    const y = getY(pt.completed);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#5e6ad2";
  ctx.lineWidth = 2;
  ctx.stroke();

  // 2. Draw Failed Area & Line (#ef4444)
  const hasFailed = series.some(pt => pt.failed > 0);
  if (hasFailed) {
    ctx.beginPath();
    ctx.moveTo(getX(0), getY(0));
    series.forEach((pt, idx) => {
      ctx.lineTo(getX(idx), getY(pt.failed));
    });
    ctx.lineTo(getX(n - 1), getY(0));
    ctx.closePath();
    ctx.fillStyle = "rgba(239, 68, 68, 0.2)";
    ctx.fill();

    ctx.beginPath();
    series.forEach((pt, idx) => {
      const x = getX(idx);
      const y = getY(pt.failed);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#ef4444";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // 3. Draw Time Labels on X-axis
  const labelStep = Math.max(1, Math.floor(n / 6));
  ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
  ctx.textAlign = "center";
  series.forEach((pt, idx) => {
    if (idx % labelStep === 0 || idx === n - 1) {
      const x = getX(idx);
      ctx.fillText(pt.time_label, x, height - 6);
    }
  });
}

window.addEventListener("resize", () => {
  if (currentTab === "history" && cachedTimeseriesData) {
    renderThroughputCanvas(cachedTimeseriesData.throughput_series);
  }
});

async function fetchHistory() {
  try {
    const status = document.getElementById("history-filter-status")?.value || "";
    const taskName = document.getElementById("history-search-task")?.value.trim() || "";

    const params = new URLSearchParams({ limit: "50" });
    if (status) params.append("status", status);
    if (taskName) params.append("task_name", taskName);

    const res = await fetch(`${API_BASE}/api/jobs/history?${params.toString()}`);
    const jobs = await res.json();
    const tbody = document.getElementById("history-table");
    const countBadge = document.getElementById("history-count-badge");

    if (countBadge) countBadge.innerText = `${jobs.length} registros`;

    if (!tbody) return;
    if (jobs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--ink-subtle);">Nenhuma execução encontrada para os filtros selecionados.</td></tr>`;
      return;
    }

    tbody.innerHTML = jobs.map(j => {
      let badgeClass = "badge-pending";
      if (j.status === "completed") badgeClass = "badge-completed";
      else if (j.status === "failed") badgeClass = "badge-failed";
      else if (j.status === "active") badgeClass = "badge-active";
      else if (j.status === "delayed" || j.status === "retrying") badgeClass = "badge-delayed";

      let durationHtml = "--";
      if (j.duration !== null && j.duration !== undefined) {
        const ms = j.duration * 1000;
        const humanStr = formatDuration(ms);
        const msStr = `${ms.toFixed(1)} ms`;
        if (ms >= 1000) {
          durationHtml = `<div style="font-weight: 500;">${humanStr}</div><div style="font-size: 11px; color: var(--ink-subtle);">${msStr}</div>`;
        } else {
          durationHtml = `<div>${humanStr}</div>`;
        }
      }
      const timeStr = j.completed_at ? timeAgo(j.completed_at) : (j.started_at ? `Iniciado ${timeAgo(j.started_at)}` : timeAgo(j.created_at));

      // Build Progress Bar Cell
      let progressHtml = "--";
      const pct = j.progress !== undefined && j.progress !== null ? Number(j.progress) : (j.status === "completed" ? 100 : 0);
      const msg = j.progress_message || "";
      const barStatusClass = j.status === "active" ? "active" : (j.status === "failed" ? "failed" : (j.status === "completed" ? "completed" : ""));

      if (j.status === "active" || j.status === "retrying" || j.status === "completed" || j.progress > 0) {
        progressHtml = `
          <div class="progress-cell">
            <div class="progress-text">
              <span>${pct.toFixed(0)}%</span>
              <span style="font-size: 10px; color: var(--ink-subtle);">${escapeHtml(j.status)}</span>
            </div>
            <div class="progress-bar-container">
              <div class="progress-bar-fill ${barStatusClass}" style="width: ${pct}%;"></div>
            </div>
            ${msg ? `<div class="progress-msg" title="${escapeHtml(msg)}">${escapeHtml(msg)}</div>` : ''}
          </div>
        `;
      }

      return `
        <tr>
          <td><span class="badge ${badgeClass}">${j.status.toUpperCase()}</span></td>
          <td><code style="cursor: pointer; text-decoration: underline;" onclick="openJobTraceModal('${j.id}')">${j.id.substring(0, 8)}</code></td>
          <td><strong>${escapeHtml(j.task_name)}</strong></td>
          <td><code>${escapeHtml(j.queue)}</code></td>
          <td>${progressHtml}</td>
          <td>${durationHtml}</td>
          <td>${escapeHtml(j.worker_id || "--")}</td>
          <td>${timeStr}</td>
          <td>
            <div class="action-group">
              <button class="btn-action" onclick="openJobTraceModal('${j.id}')">🔍 Trace & Logs</button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to fetch history", err);
  }
}

async function openJobTraceModal(jobId) {
  try {
    window._activeTraceJobId = jobId;
    const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
    if (!res.ok) throw new Error("Job não encontrado");
    const job = await res.json();

    document.getElementById("lgtm-modal-title").innerText = `Job ${job.id.substring(0, 8)}: ${job.task_name}`;
    document.getElementById("lgtm-modal-subtitle").innerText = `Fila: [${job.queue}] | Status: ${job.status.toUpperCase()} | Worker: ${job.worker_id || 'Nenhum'}`;

    // 0. Render Live Progress Widget in Modal Header
    const progressContainer = document.getElementById("lgtm-progress-container");
    if (progressContainer) {
      const pct = job.progress !== undefined && job.progress !== null ? Number(job.progress) : (job.status === "completed" ? 100 : 0);
      const barClass = job.status === "active" ? "active" : (job.status === "failed" ? "failed" : (job.status === "completed" ? "completed" : ""));
      progressContainer.innerHTML = `
        <div style="margin-bottom: 16px; padding: 12px; background: var(--surface-2); border: 1px solid var(--hairline); border-radius: var(--radius-sm);">
          <div class="progress-text">
            <span style="font-weight: 500;" id="trace-progress-title">Progresso da Execução</span>
            <span id="trace-progress-pct" style="font-family: var(--font-mono); font-weight: 600;">${pct.toFixed(0)}%</span>
          </div>
          <div class="progress-bar-container" style="height: 6px; margin-top: 6px;">
            <div class="progress-bar-fill ${barClass}" id="trace-progress-bar" style="width: ${pct}%;"></div>
          </div>
          <div class="progress-msg" id="trace-progress-msg" style="margin-top: 4px; font-size: 11px; max-width: 100%;">${escapeHtml(job.progress_message || (job.status === 'completed' ? 'Concluído com sucesso' : (job.status === 'active' ? 'Executando...' : '')))}</div>
        </div>
      `;
    }

    // 1. Render Tempo Trace Timeline
    const timelineContainer = document.getElementById("lgtm-trace-timeline");
    const steps = [
      {
        name: "Enfileirado",
        time: job.created_at,
        meta: `Criado e adicionado à fila '${job.queue}'`,
        status: "completed"
      }
    ];

    if (job.started_at) {
      steps.push({
        name: "Processando",
        time: job.started_at,
        meta: `Consumido pelo worker '${job.worker_id || 'dev-worker'}'`,
        status: job.status === "active" ? "active" : "completed"
      });
    }

    if (job.completed_at) {
      const durMs = job.duration !== null && job.duration !== undefined ? job.duration * 1000 : null;
      const durFormatted = durMs !== null ? formatDuration(durMs, { includeExact: true }) : "";
      steps.push({
        name: job.status === "failed" ? "Falhou (DLQ)" : "Finalizado",
        time: job.completed_at,
        meta: job.status === "failed" ? `Erro: ${job.error || 'Falha'} (Duração: ${durFormatted})` : `Concluído com sucesso em ${durFormatted}`,
        status: job.status === "failed" ? "failed" : "completed"
      });
    }

    timelineContainer.innerHTML = steps.map((s, idx) => `
      <div class="trace-step">
        <div class="trace-dot ${s.status}"></div>
        <div class="trace-step-name">${s.name}</div>
        <div class="trace-step-meta">${timeAgo(s.time)} — ${escapeHtml(s.meta)}</div>
      </div>
    `).join("");

    // 2. Render Loki Logs Console
    const logsContainer = document.getElementById("lgtm-logs-console");
    const logs = job.logs && job.logs.length > 0 ? job.logs : [`[INFO] Job registrado com ID ${job.id}`];
    if (job.traceback) {
      logs.push(`[ERROR] Traceback: ${job.traceback}`);
    }

    logsContainer.innerHTML = logs.map(l => {
      const isErr = l.includes("[ERROR]") || l.includes("Falha") || l.includes("Traceback");
      return `<div class="log-entry"><span class="${isErr ? 'log-err' : 'log-msg'}">${escapeHtml(l)}</span></div>`;
    }).join("");

    // 3. Render Payload & Output
    const payloadViewer = document.getElementById("lgtm-payload-viewer");
    const payloadData = {
      args: job.args,
      kwargs: job.kwargs,
      result: job.result,
      error: job.error,
      retry_count: job.retry_count,
      max_retries: job.max_retries,
      duration_seconds: job.duration
    };
    payloadViewer.innerText = JSON.stringify(payloadData, null, 2);

    openModal("modal-lgtm-trace");
  } catch (err) {
    toast.error("Erro ao abrir observabilidade", err.message);
  }
}

// --- Maintenance / Redis Flush Controller ---

function openMaintenanceModal() {
  openModal("modal-maintenance");
}

async function executeMaintenanceFlush(target) {
  const targetNames = {
    queues: "Filas e Jobs",
    history: "Histórico de Execuções",
    all: "Banco de Dados Redis Completo (Reset Total)",
  };

  try {
    const res = await fetch(`${API_BASE}/api/maintenance/flush`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target }),
    });

    if (res.ok) {
      closeModal("modal-maintenance");
      toast.success("Limpeza Concluída", `${targetNames[target] || target} foi limpo com sucesso no Redis.`);
      logEvent("SYSTEM", `Limpeza do Redis executada: ${target}`);
      refreshCurrentTab();
      fetchOverview();
    } else {
      const err = await res.json();
      toast.error("Erro na Limpeza", err.detail || "Falha ao executar limpeza no Redis.");
    }
  } catch (err) {
    toast.error("Falha na Requisição", err.message);
  }
}

// --- Dropdown Menu Controller ---

function toggleDropdown(menuId) {
  const menu = document.getElementById(menuId);
  const parent = menu?.closest('.dropdown');
  if (!parent) return;
  const isOpen = parent.classList.contains('open');
  closeDropdowns();
  if (!isOpen) {
    parent.classList.add('open');
  }
}

function closeDropdowns() {
  document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.dropdown')) {
    closeDropdowns();
  }
});

// --- Queue Management (Create & Delete) ---

function openCreateQueueModal() {
  const input = document.getElementById("create-queue-name");
  if (input) {
    input.value = "";
    setTimeout(() => input.focus(), 50);
  }
  openModal("modal-create-queue");
}

async function handleCreateQueueSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("create-queue-name");
  const name = input?.value.trim();
  if (!name) {
    toast.warning("Nome da Fila", "Por favor informe um nome válido para a fila.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/queues`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });

    if (res.ok) {
      closeModal("modal-create-queue");
      toast.success("Fila criada", `A fila [${name}] foi registrada com sucesso no Redis.`);
      logEvent("QUEUE", `Nova fila registrada: [${name}]`);
      fetchOverview();
      if (currentTab === "queues") fetchTasks();
    } else {
      const errData = await res.json().catch(() => ({}));
      toast.error("Erro ao criar fila", errData.detail || "Falha ao registrar fila.");
    }
  } catch (err) {
    toast.error("Falha na requisição", err.message);
  }
}

async function deleteQueue(queueName) {
  if (queueName === "default") {
    toast.warning("Ação não permitida", "A fila padrão 'default' não pode ser excluída.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/queues/${queueName}`, { method: "DELETE" });
    if (res.ok) {
      toast.info("Fila excluída", `A fila [${queueName}] foi removida do Redis.`);
      logEvent("QUEUE", `Fila removida: [${queueName}]`);
      fetchOverview();
      if (currentTab === "queues") fetchTasks();
    } else {
      const errData = await res.json().catch(() => ({}));
      toast.error("Erro ao excluir fila", errData.detail || "Falha ao remover fila.");
    }
  } catch (err) {
    toast.error("Falha na requisição", err.message);
  }
}

// --- Command Palette Controller (Ctrl+K / ⌘K) ---

let cmdSelectedIndex = 0;
const defaultCommands = [
  { id: "new-task", icon: "⚡", title: "Nova Tarefa", desc: "Enfileirar job imediato ou com delay", action: () => openEnqueueModal() },
  { id: "new-cron", icon: "⏰", title: "Novo Cron / Agendamento", desc: "Programar rotina periódica ou intervalo", action: () => openScheduleModal() },
  { id: "new-queue", icon: "📦", title: "Nova Fila", desc: "Registrar uma nova fila no Redis", action: () => openCreateQueueModal() },
  { id: "new-worker", icon: "🤖", title: "Iniciar Novo Worker", desc: "Spawnar processo de worker dinâmico", action: () => openSpawnWorkerModal() },
  { id: "tab-overview", icon: "📊", title: "Ir para: Visão Geral", desc: "Métricas globais de filas e telemetria", action: () => switchTab("overview") },
  { id: "tab-workers", icon: "👥", title: "Ir para: Workers", desc: "Gerenciar workers ativos, pausar e retomar", action: () => switchTab("workers") },
  { id: "tab-queues", icon: "📋", title: "Ir para: Filas & Tarefas", desc: "Explorar funções @task registradas", action: () => switchTab("queues") },
  { id: "tab-schedules", icon: "📅", title: "Ir para: Cron & Agendamentos", desc: "Ver rotinas ativas e disparar", action: () => switchTab("schedules") },
  { id: "tab-dlq", icon: "⚠️", title: "Ir para: Dead Letter Queue (DLQ)", desc: "Inspecionar e fazer replay de falhas", action: () => switchTab("dlq") },
  { id: "tab-history", icon: "📈", title: "Ir para: Observabilidade & Histórico", desc: "Métricas LGTM, traces Tempo e logs Loki", action: () => switchTab("history") },
  { id: "flush-redis", icon: "🧹", title: "Limpar Redis & Manutenção", desc: "Abrir painel de flush atômico do Redis", action: () => openMaintenanceModal() },
];

function openCommandPalette() {
  openModal("modal-command-palette");
  const input = document.getElementById("cmd-search-input");
  if (input) {
    input.value = "";
    setTimeout(() => input.focus(), 50);
  }
  renderCommandResults(defaultCommands);
}

function handleCommandSearch(query) {
  const q = (query || "").trim().toLowerCase();
  if (!q) {
    renderCommandResults(defaultCommands);
    return;
  }

  const filtered = defaultCommands.filter(c => 
    c.title.toLowerCase().includes(q) || c.desc.toLowerCase().includes(q)
  );

  // Search dynamically in registered tasks
  const matchingTasks = (cachedTasks || []).filter(t => 
    t.name.toLowerCase().includes(q) || (t.queue && t.queue.toLowerCase().includes(q))
  ).map(t => ({
    id: `task-${t.name}`,
    icon: "⚡",
    title: `Enfileirar: ${t.name}`,
    desc: `Fila: [${t.queue}] | Timeout: ${t.timeout ? `${t.timeout}s` : 'Sem limite'}`,
    action: () => quickEnqueueTask(t.name, t.queue)
  }));

  renderCommandResults([...filtered, ...matchingTasks]);
}

function renderCommandResults(list) {
  const container = document.getElementById("cmd-palette-results");
  if (!container) return;
  cmdSelectedIndex = 0;

  if (list.length === 0) {
    container.innerHTML = `<div style="padding: 16px; text-align: center; color: var(--ink-subtle); font-size: 13px;">Nenhum comando ou tarefa encontrada.</div>`;
    return;
  }

  window._activeCommandsList = list;

  container.innerHTML = list.map((item, idx) => `
    <div class="cmd-item ${idx === 0 ? 'selected' : ''}" data-index="${idx}" onclick="executeCommandByIndex(${idx})">
      <div class="cmd-item-left">
        <span style="font-size: 15px;">${item.icon}</span>
        <div>
          <div style="font-weight: 500; color: var(--ink); font-size: 13px;">${escapeHtml(item.title)}</div>
          <div style="font-size: 11px; color: var(--ink-subtle);">${escapeHtml(item.desc)}</div>
        </div>
      </div>
      <span style="font-size: 11px; color: var(--ink-tertiary);">↵</span>
    </div>
  `).join("");
}

function executeCommandByIndex(index) {
  const list = window._activeCommandsList || defaultCommands;
  if (list[index] && typeof list[index].action === "function") {
    closeModal("modal-command-palette");
    list[index].action();
  }
}

function handleCommandKeyDown(e) {
  const list = window._activeCommandsList || [];
  if (list.length === 0) return;

  if (e.key === "ArrowDown") {
    e.preventDefault();
    cmdSelectedIndex = (cmdSelectedIndex + 1) % list.length;
    updateSelectedCmdItem();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    cmdSelectedIndex = (cmdSelectedIndex - 1 + list.length) % list.length;
    updateSelectedCmdItem();
  } else if (e.key === "Enter") {
    e.preventDefault();
    executeCommandByIndex(cmdSelectedIndex);
  }
}

function updateSelectedCmdItem() {
  document.querySelectorAll(".cmd-item").forEach((el, idx) => {
    el.classList.toggle("selected", idx === cmdSelectedIndex);
    if (idx === cmdSelectedIndex) {
      el.scrollIntoView({ block: "nearest" });
    }
  });
}

// Global Keyboard Shortcut: Ctrl+K / Cmd+K
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    const modal = document.getElementById("modal-command-palette");
    if (modal?.classList.contains("show")) {
      closeModal("modal-command-palette");
    } else {
      openCommandPalette();
    }
  } else if (e.key === "Escape") {
    closeModal("modal-command-palette");
    closeDropdowns();
  }
});

