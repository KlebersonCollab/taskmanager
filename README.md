# TaskManager ⚡

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2%2B%20%7C%205.0%2B-092E20?style=for-the-badge&logo=django&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7%2B_AOF_Durable-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![UI](https://img.shields.io/badge/UI-Linear_Dark_System-5E6AD2?style=for-the-badge&logo=linear&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Engine moderna de background tasks em Python inspirada no Celery e BullMQ.**  
*Rate Limiting & Concorrência • Progresso em Tempo Real • Live Log Streaming • Observabilidade Canvas Nativa • Webhooks Multi-Plataforma • Agendador Cron Dinâmico • Dead Letter Queue Multi-Fila • Dashboard SPA Linear Dark.*

<br/>

<img src="docs/images/01_dashboard_overview.png" alt="TaskManager Dashboard Overview" width="100%" style="border-radius: 12px; border: 1px solid #23252a; box-shadow: 0 20px 40px rgba(0,0,0,0.6);" />

</div>

---

## 🌟 Principais Destaques

- **⚡ Rate Limiting Distribuído (Token Bucket em Redis)**: Controle rigoroso de vazão por tarefa (`rate_limit="10/s"`, `"100/m"`, `"1000/h"`, `"5000/d"`) para evitar erros `HTTP 429 Too Many Requests` e bloqueios em APIs externas.
- **🔒 Concorrência Máxima por Tarefa (`max_concurrency`)**: Semáforo distribuído em Redis que limita quantas instâncias de uma mesma função podem rodar simultaneamente em todo o cluster, protegendo CPU e pools de banco de dados.
- **📈 Progresso em Tempo Real & Live Log Streaming**: Injeção automática de `TaskContext` nas tarefas para emissão de progresso (`0-100%`) e streaming de logs linha a linha em tempo real via WebSockets.
- **📊 Observabilidade Nativa Self-Contained (Zero Prometheus / Zero Grafana)**:
  - **📈 Gráficos Temporais Canvas**: Curvas de área de throughput (sucesso vs falhas) com escala de alta densidade DPI nas janelas de `15m`, `30m`, `1h` e `24h`.
  - **⏱️ Histograma & Percentis de Latência**: Cálculo exato de **P50**, **P90**, **P95** e **P99** e distribuição em faixas de tempo (`<50ms`, `50-200ms`, `200-500ms`, etc.).
  - **📋 Ranking por Tarefa**: Volume, taxa de sucesso % e latência média por task.
- **🔔 Canais de Alerta Multi-Plataforma (Webhooks)**:
  - Notificações automáticas instantâneas ao esgotar retentativas (DLQ) para **Telegram**, **Slack**, **Discord**, **Microsoft Teams** e **Webhooks HTTP Genéricos** com assinatura secreta.
  - Botão de envio de alerta de teste (*Test Ping*) direto pelo dashboard com feedback em tempo real.
- **🚀 Asyncio & Sync Worker Runtime**: Suporte nativo para corrotinas assíncronas (`async def`) e funções síncronas (`def`), com concorrência ajustável, circuit breaker de CPU/RAM e timeouts granulares.
- **📦 Redis Broker com Durabilidade AOF**: Filas atômicas (`LPOP`/`BLPOP`), conjuntos ordenados para jobs agendados e histórico, e persistência AOF com garantia de *Zero Data Loss*.
- **🧠 Fallback In-Memory Automático**: Modo de desenvolvimento zero-dependência (`fakeredis`) quando o Redis local não estiver em execução.
- **✨ Decorator `@task` & Introspecção**: Enfileiramento via `.delay(*args, **kwargs)` ou `.apply_async(...)` com geração automática de schemas e assinatura de parâmetros.
- **⏰ Agendador Cron & Intervalos em Tempo Real**: Sintaxe padrão de 5 posições (`*/5 * * * *`) ou intervalo em segundos com distributed leader locking.
- **🛡️ Resiliência & Dead Letter Queue (DLQ)**: Retentativas com exponential backoff, Dead Letter Queue (DLQ) com inspeção de stacktrace e *One-Click Replay*.
- **🎨 Design System Linear Dark**: Interface minimalista com atalho global **`Ctrl+K` (Command Palette)**, menu de ação unificado **`+ Criar ▾`**, e badges para Rate Limit e Concorrência.
- **🔌 Plug-and-Play em Qualquer Framework**: Use como aplicação independente ou embarque facilmente dentro do seu projeto **FastAPI**, **Django** ou **Flask**.

---

## 📦 Como Usar o TaskManager no seu Projeto (Biblioteca / Framework)

Você pode adicionar o TaskManager ao seu projeto Python existente via PyPI:

```bash
# Instalar no seu projeto via PyPI:
pip install taskmanager-engine
# ou usando UV:
uv add taskmanager-engine

# Dica: Para forçar o download da versão mais recente ignorando o cache local do UV:
uv sync --refresh
# ou
uv add "taskmanager-engine>=0.3.0" --refresh
```

---

### Método 1: Embutir no FastAPI / Starlette (Sub-Aplicação / Mount)

Monte o dashboard, os websockets e os endpoints do TaskManager diretamente dentro da sua aplicação FastAPI existente:

```python
# main.py
import asyncio
from fastapi import FastAPI
from taskmanager import TaskManager, task, TaskContext

# 1. Cria sua aplicação principal
app = FastAPI(title="Minha API Principal")

# 2. Configura a instância do TaskManager apontando para o Redis
tm = TaskManager(redis_url="redis://localhost:6379/0", prefix="meu_app")

# 3. Define tarefas com Rate Limit, Concorrência e TaskContext
@task(
    name="whatsapp.enviar_cobranca",
    queue="mensagens",
    rate_limit="10/s",       # Máximo 10 requisições por segundo (Token Bucket)
    max_concurrency=2,       # Máximo 2 execuções simultâneas no cluster
    max_retries=3,
)
async def enviar_whatsapp(telefone: str, valor: float, ctx: TaskContext):
    await ctx.append_log(f"Disparando cobrança no valor de R$ {valor:.2f} para {telefone}...")
    await ctx.update_progress(50.0, "Consultando API de mensageria")
    await asyncio.sleep(0.3)
    await ctx.append_log("Mensagem entregue com sucesso!")
    await ctx.update_progress(100.0, "Concluído")
    return {"status": "enviado", "telefone": telefone}

# 4. Monta o dashboard do TaskManager sob a rota /tasks
tm.mount_to(app, path="/tasks")

@app.post("/cobrancas/enviar")
async def cobrar_cliente(telefone: str, valor: float):
    # Enfileira o job em background
    job = await enviar_whatsapp.delay(telefone=telefone, valor=valor)
    return {"mensagem": "Cobrança enfileirada!", "job_id": job.id}
```

*Ao acessar `http://localhost:8000/tasks/`, o dashboard completo estará rodando dentro da sua própria aplicação!*

---

### Método 2: Integração com Django (`taskmanager.contrib.django`)

O TaskManager possui integração de primeira classe com o ecossistema Django:

1. Adicione `'taskmanager.contrib.django'` ao seu `INSTALLED_APPS` em `settings.py`:
```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    ...,
    "taskmanager.contrib.django",  # <- Adicione aqui
    "meu_app_vendas",
]

# Configurações opcionais do Redis
TASKMANAGER_REDIS_URL = "redis://localhost:6379/0"
TASKMANAGER_REDIS_PREFIX = "django_app"
```

2. Crie um arquivo `tasks.py` dentro dos seus apps Django:
```python
# meu_app_vendas/tasks.py
from taskmanager import task, TaskContext

@task(
    name="vendas.gerar_fatura",
    queue="faturamento",
    rate_limit="50/m",      # Máximo 50 faturas por minuto
    max_concurrency=3,      # Máximo 3 faturas simultâneas
    max_retries=2,
)
async def gerar_fatura(pedido_id: int, ctx: TaskContext):
    await ctx.append_log(f"Processando fatura do pedido #{pedido_id}")
    await ctx.update_progress(50.0, "Consultando gateway de pagamento...")
    # ...
    await ctx.update_progress(100.0, "Fatura emitida com sucesso!")
    return {"fatura_id": 98765, "pedido_id": pedido_id}
```

3. Adicione as URLs no seu `urls.py`:
```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tasks/", include("taskmanager.contrib.django.urls")),  # <- Dashboard
]
```

4. Execute workers e schedulers nativamente com `manage.py`:
```bash
# Iniciar worker consumindo as filas do Django:
python manage.py run_worker --queues faturamento,default --concurrency 5

# Iniciar o scheduler de rotinas cron:
python manage.py run_scheduler
```

---

### Método 3: Modo Standalone / CLI (Sidecar Desacoplado)

Se preferir manter o TaskManager como um serviço separado (sidecar):

```bash
# Modo Dev (Dashboard + Worker + Scheduler apontando para seus módulos de tarefas):
taskmanager dev --modules example_tasks --port 8000

# Processos isolados para Produção:
taskmanager worker --modules example_tasks --queues emails,reports,default -c 8
taskmanager scheduler --modules example_tasks
taskmanager server --port 8080
```

---

## 🔔 Configuração de Alertas & Webhooks

Você pode cadastrar canais de notificação diretamente pela interface do dashboard (ícone `🔔` ou menu `+ Criar ▾`) ou via API REST:

```bash
# Exemplo: Cadastrar canal do Telegram para falhas na DLQ
curl -X POST http://localhost:8000/api/alerts/channels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Telegram Ops Bot",
    "channel_type": "telegram",
    "target_url": "https://api.telegram.org/bot<SEU_BOT_TOKEN>/sendMessage",
    "telegram_chat_id": "6121374069",
    "events": ["job:failed"],
    "enabled": true
  }'

# Exemplo: Cadastrar canal do Discord
curl -X POST http://localhost:8000/api/alerts/channels \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Discord #alertas-ops",
    "channel_type": "discord",
    "target_url": "https://discord.com/api/webhooks/12345/abcdef",
    "events": ["job:failed"],
    "enabled": true
  }'
```

---

## 📂 Pasta de Exemplos Práticos (`samples/` & `example_tasks.py`)

O repositório inclui projetos de exemplo completos e prontos para rodar:

| Exemplo | Descrição | Como Executar |
| :--- | :--- | :--- |
| [📁 example_tasks.py](example_tasks.py) | Coleção completa de tarefas demonstrando Rate Limiting (`5/s`), Concorrência (`max 2`), Streaming de Logs e DLQ. | `uv run taskmanager dev --modules example_tasks` |
| [📁 samples/fastapi_sample](samples/fastapi_sample) | API FastAPI completa montando o TaskManager em `/tasks/` com checkout, streaming e e-mail. | `uv run python -m samples.fastapi_sample.main` |
| [📁 samples/django_sample](samples/django_sample) | Projeto Django configurado com `taskmanager.contrib.django`, `tasks.py` e comandos `manage.py`. | `python samples/django_sample/manage.py run_worker` |
| [📁 samples/standalone_cli](samples/standalone_cli) | Demonstração de uso puro via linha de comando desacoplada. | `uv run taskmanager dev --modules samples.standalone_cli.tasks` |

---

## 🛠️ Como Compilar e Publicar a Biblioteca (PyPI)

Para gerar os pacotes `.whl` (Wheel) e `.tar.gz` (Source Distribution) com todos os arquivos de UI embutidos:

```bash
# 1. Atualizar o lockfile local
uv lock
uv sync --all-extras

# 2. Compilar os artefatos de distribuição
uv build

# 3. Testar instalação local em modo editável
pip install -e .

# 4. Publicar no PyPI
uv publish --token <SEU_TOKEN_PYPI>

# 5. Em projetos externos, ignorar o cache do UV para baixar a nova versão imediatamente:
uv sync --refresh
# ou
uv add "taskmanager-engine>=0.3.0" --refresh
```

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

### 6. Observabilidade Nativa & Trace Waterfall (LGTM Stack)
Inspecione a linha do tempo exata de execução de cada tarefa com logs capturados e payloads serializados.
<img src="docs/images/06_observability_trace.png" alt="Observabilidade e Tracing" width="100%" style="border-radius: 8px; border: 1px solid #23252a; margin-bottom: 24px;" />

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
# Executar suíte completa de testes (42 testes unitários e de integração)
uv run pytest -v tests/

# Executar linter de código
uv run ruff check taskmanager tests samples example_tasks.py

# Sensor de Spec Drift (SDD)
node .agents/scripts/check-spec-drift.js
```

---

## 📄 Licença
Distribuído sob a licença [MIT](LICENSE). Pronto para uso individual ou corporativo.
