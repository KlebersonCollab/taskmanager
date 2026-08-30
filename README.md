# TaskManager ⚡

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7%2B_AOF_Durable-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![UI](https://img.shields.io/badge/UI-Linear_Dark_System-5E6AD2?style=for-the-badge&logo=linear&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Engine moderna de execução e gerenciamento de background tasks em Python inspirada no Celery e BullMQ.**  
*Agendador Cron Dinâmico • Observabilidade LGTM Completa • Dead Letter Queue Multi-Fila • Telemetria com Backpressure • Dashboard SPA Linear Dark.*

<br/>

<img src="docs/images/01_dashboard_overview.png" alt="TaskManager Dashboard Overview" width="100%" style="border-radius: 12px; border: 1px solid #23252a; box-shadow: 0 20px 40px rgba(0,0,0,0.6);" />

</div>

---

## 🌟 Principais Destaques

- **🚀 Asyncio & Sync Worker Runtime**: Suporte nativo e transparente para corrotinas assíncronas (`async def`) e funções síncronas (`def`), com concorrência ajustável e timeouts granulares.
- **📦 Redis Broker com Durabilidade AOF**: Sem brokers pesados. Utiliza listas atômicas do Redis (`LPOP`/`BLPOP`), conjuntos ordenados para jobs agendados e histórico, e persistência AOF para garantia de *Zero Data Loss*.
- **🧠 Fallback In-Memory Automático**: Modo de desenvolvimento zero-dependência (`fakeredis`) quando o Redis local não estiver em execução.
- **✨ Decorator `@task` & Introspecção**: Enfileiramento via `.delay(*args, **kwargs)` ou `.apply_async(...)` com geração automática de schemas e payload no painel.
- **⏰ Agendador Cron & Intervalos em Tempo Real**: Sintaxe padrão de 5 posições (`*/5 * * * *`) ou intervalo em segundos com distributed leader locking e execução garantida.
- **🛡️ Resiliência, DLQ & Backpressure**: Retentativas com exponential backoff, Dead Letter Queue (DLQ) com inspeção de stacktrace e *One-Click Replay*. Circuit breaker de CPU e Memória RSS por worker.
- **📊 Observabilidade LGTM Nativa**:
  - **📈 Mimir / Prometheus**: KPIs em tempo real (Taxa de Sucesso %, Duração Média ms, Latência P95 ms, Throughput/min).
  - **📜 Loki**: Console de logs de execução, erros e tracebacks capturados.
  - **⏱️ Tempo**: Linha do tempo em cascata (Enqueued ➔ Dequeued ➔ Executing ➔ Finished/Failed).
- **🎨 Design System Linear Dark**: Interface minimalista com atalho global **`Ctrl+K` (Command Palette)**, menu de ação unificado **`+ Criar ▾`**, e realce suave de linhas.

---

## 📸 Galeria de Telas do Dashboard

### 1. Visão Geral & Métricas em Tempo Real
Acompanhe o estado de todas as filas, consumo de hardware dos workers e log de eventos ao vivo via WebSockets.
<img src="docs/images/01_dashboard_overview.png" alt="Visão Geral" width="100%" style="border-radius: 8px; border: 1px solid #23252a; margin-bottom: 24px;" />

---

### 2. Menu Unificado `+ Criar ▾` & Paleta de Comandos (`Ctrl+K`)
Navegue e execute qualquer ação em milissegundos sem tirar as mãos do teclado.
<div align="center">
  <img src="docs/images/08_quick_create_menu.png" alt="Menu Criar" width="48%" style="border-radius: 8px; border: 1px solid #23252a; margin-right: 2%;" />
  <img src="docs/images/07_command_palette.png" alt="Command Palette Ctrl+K" width="48%" style="border-radius: 8px; border: 1px solid #23252a;" />
</div>

---

### 3. Gerenciamento de Workers & Proteção de Recursos
Monitore o uso de CPU/RAM de cada worker individual e pause ou interrompa processos com um clique.
<img src="docs/images/02_workers_management.png" alt="Gerenciamento de Workers" width="100%" style="border-radius: 8px; border: 1px solid #23252a; margin-bottom: 24px;" />

---

### 4. Agendamentos Cron & Rotinas Periódicas
Crie e edite agendamentos em tempo real sem precisar reiniciar os serviços ou fazer deploy.
<img src="docs/images/04_cron_schedules.png" alt="Agendamentos Cron" width="100%" style="border-radius: 8px; border: 1px solid #23252a; margin-bottom: 24px;" />

---

### 5. Dead Letter Queue (DLQ) & Inspeção de Falhas
Monitore jobs que esgotaram retentativas, visualize o stacktrace completo e faça o replay imediato para a fila.
<img src="docs/images/05_dlq_inspector.png" alt="Dead Letter Queue" width="100%" style="border-radius: 8px; border: 1px solid #23252a; margin-bottom: 24px;" />

---

### 6. Observabilidade & Trace Waterfall (LGTM Stack)
Inspecione a linha do tempo exata de execução de cada tarefa com logs capturados e payloads serializados.
<img src="docs/images/06_observability_trace.png" alt="Observabilidade e Tracing" width="100%" style="border-radius: 8px; border: 1px solid #23252a; margin-bottom: 24px;" />

---

## 🚀 Instalação Rápida (com `uv`)

```bash
# 1. Clonar o repositório
git clone https://github.com/usuario/taskmanager.git
cd taskmanager

# 2. Sincronizar o ambiente virtual e dependências
uv sync --all-extras
```

---

## 💻 Comandos da CLI

O TaskManager possui 4 comandos principais para desenvolvimento e produção:

### 1. `taskmanager dev` (Modo Tudo-em-Um para Desenvolvimento)
Inicia o **Servidor API + Dashboard Web**, o **Worker** e o **Scheduler** em um único comando concorrente.

```bash
# Iniciar ambiente dev com tarefas de exemplo
uv run taskmanager dev --modules example_tasks

# Customizar porta, filas e guardrails de memória
uv run taskmanager dev --port 8000 -c 8 --max-memory-mb 512 -m example_tasks
```

---

### 2. `taskmanager worker` (Processo de Worker Dedicado)
Inicia um processo de worker independente com balanceamento de carga automático via Redis.

```bash
# Worker de alta concorrência para e-mails
uv run taskmanager worker -n worker-emails -q emails -c 10 -m example_tasks

# Worker com teto de memória e múltiplas filas
uv run taskmanager worker -n worker-reports -q reports,default,payments -c 4 --max-memory-mb 1024 -m example_tasks
```

---

### 3. `taskmanager scheduler` (Daemon do Cron Distribuído)
Inicia o scheduler distribuído com leader locking automático no Redis.

```bash
uv run taskmanager scheduler -m example_tasks
```

---

### 4. `taskmanager server` (Servidor API & Dashboard Standalone)
Inicia apenas o servidor web FastAPI e a interface SPA:

```bash
uv run taskmanager server --host 0.0.0.0 --port 8000 --app-module example_tasks
```

---

## 🐍 Guia do SDK Python

### 1. Definindo Tarefas com `@task`

```python
# example_tasks.py
import asyncio
from taskmanager import task

# Tarefa Assíncrona com Exponential Backoff
@task(
    name="emails.send_welcome_email",
    queue="emails",
    max_retries=3,
    retry_backoff=2.0,  # Retries em 2s, 4s, 8s
    timeout=10.0,
)
async def send_welcome_email(email: str, name: str) -> dict:
    """Dispara e-mail de boas-vindas assincronamente."""
    await asyncio.sleep(1.0)
    print(f"📧 E-mail enviado para {name} <{email}>")
    return {"status": "delivered", "recipient": email}


# Tarefa Síncrona Pesada (Executada em Threadpool)
@task(
    name="reports.generate_sales_report",
    queue="reports",
    max_retries=1,
    timeout=60.0,
)
def generate_sales_report(year: int, month: int, department: str = "Geral") -> dict:
    """Gera relatório PDF em background sem travar o event loop."""
    return {"file": f"/exports/{department}_{year}_{month:02d}.pdf"}
```

### 2. Enfileirando Jobs via Código

```python
# enqueue_examples.py
import asyncio
from example_tasks import send_welcome_email, generate_sales_report

async def main():
    # 1. Execução Imediata (.delay)
    job1 = await send_welcome_email.delay("cliente@empresa.com", "Carlos Silva")
    print(f"Job enfileirado: {job1.id}")

    # 2. Execução Agendada / Delay (.apply_async)
    job2 = await generate_sales_report.apply_async(
        kwargs={"year": 2026, "month": 8, "department": "Financeiro"},
        delay=30.0,  # Executa após 30 segundos
        queue="reports",
        priority=1,
    )
    print(f"Job agendado: {job2.id}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🐳 Stack Docker & Docker Compose

Suba o cluster completo em contêineres com um único comando:

```bash
# Iniciar todos os serviços com Redis AOF persistente
docker compose up --build -d

# Visualizar status e healthchecks
docker compose ps

# Escalar workers dinamicamente
docker compose up -d --scale worker-emails=3
```

---

## 🧪 Testes & Qualidade

```bash
# Executar suíte completa de testes
uv run pytest -v tests/

# Executar linter de código
uv run ruff check taskmanager tests example_tasks.py enqueue_examples.py scripts/

# Sensor de Spec Drift (SDD)
node .agents/scripts/check-spec-drift.js
```

---

## 📄 Licença
Distribuído sob a licença [MIT](LICENSE). Pronto para uso individual ou corporativo.
