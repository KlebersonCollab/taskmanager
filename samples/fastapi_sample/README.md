# Exemplo: Integração FastAPI + TaskManager (Sub-App)

Este exemplo demonstra como adicionar o **TaskManager** dentro de uma aplicação FastAPI existente, disponibilizando o dashboard completo no caminho `/tasks/`.

---

## 🚀 Como Executar

### 1. Iniciar o Servidor FastAPI
```bash
uv run python -m samples.fastapi_sample.main
```

### 2. Acessar os Recursos
- **API Principal**: [http://localhost:8000/](http://localhost:8000/)
- **Dashboard TaskManager**: [http://localhost:8000/tasks/](http://localhost:8000/tasks/)
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Disparar Tarefas de Teste
```bash
# Disparar processamento de pedido:
curl -X POST "http://localhost:8000/comprar?order_id=PED-101&amount=450.00"

# Disparar envio de e-mail:
curl -X POST "http://localhost:8000/notificar?email=cliente@exemplo.com"
```

Abra o dashboard em [http://localhost:8000/tasks/](http://localhost:8000/tasks/) para acompanhar a execução ao vivo!
