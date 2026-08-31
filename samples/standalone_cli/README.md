# Exemplo: Uso Standalone / CLI (Sidecar)

Se você preferir executar o **TaskManager** como um processo desacoplado (sidecar) sem acoplar diretamente no código do seu servidor web:

---

## 🚀 Como Executar

### 1. Iniciar Tudo em Desenvolvimento (Dev Mode)
Inicia automaticamente o Dashboard Web, um Worker e o Scheduler:
```bash
uv run taskmanager dev --modules samples.standalone_cli.tasks --port 8000
```
Acesse o dashboard em: [http://localhost:8000/](http://localhost:8000/)

---

### 2. Em Produção (Processos Isolados)

#### Iniciar apenas o Worker:
```bash
uv run taskmanager worker --modules samples.standalone_cli.tasks --queues reports,default --concurrency 4
```

#### Iniciar apenas o Scheduler (Cron):
```bash
uv run taskmanager scheduler --modules samples.standalone_cli.tasks
```

#### Iniciar apenas o Dashboard SPA:
```bash
uv run taskmanager dashboard --port 8080 --host 0.0.0.0
```
