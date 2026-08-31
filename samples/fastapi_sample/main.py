from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from samples.fastapi_sample.tasks import process_checkout, send_email
from taskmanager import TaskManager

# 1. Configura a instância do TaskManager apontando para o Redis do seu projeto
# (Usa Redis In-Memory automático se redis_url não estiver acessível)
tm = TaskManager(redis_url="redis://localhost:6379/0", prefix="fastapi_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Opcional: Inicia um worker embutido no mesmo processo para desenvolvimento
    worker = tm.create_worker(queues=["emails", "orders", "default"], concurrency=4)
    import asyncio
    worker_task = asyncio.create_task(worker.start())
    yield
    await worker.stop()
    worker_task.cancel()


# 2. Cria a aplicação principal FastAPI
app = FastAPI(
    title="Meu E-commerce com TaskManager Integrado",
    description="Exemplo prático de como integrar o TaskManager como Sub-App no FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
)

# 3. Monta o dashboard e os endpoints do TaskManager sob o path /tasks
tm.mount_to(app, path="/tasks")


@app.get("/")
async def index():
    return {
        "message": "API Principal funcionando!",
        "dashboard_url": "http://localhost:8000/tasks/",
        "endpoints": {
            "comprar": "POST /comprar?order_id=123&amount=99.90",
            "notificar": "POST /notificar?email=user@exemplo.com",
        },
    }


@app.post("/comprar")
async def comprar(order_id: str = "PED-9981", amount: float = 249.90):
    # Enfileira a tarefa assincronamente com .delay()
    job = await process_checkout.delay(order_id=order_id, amount=amount)
    return {
        "message": "Pedido recebido! Processando em segundo plano.",
        "job_id": job.id,
        "track_in_dashboard": "http://localhost:8000/tasks/",
    }


@app.post("/notificar")
async def notificar(email: str = "cliente@empresa.com", subject: str = "Bem-vindo!"):
    job = await send_email.delay(recipient=email, subject=subject, body="Obrigado por se cadastrar!")
    return {
        "message": "E-mail enfileirado para envio.",
        "job_id": job.id,
    }


if __name__ == "__main__":
    print("🚀 Iniciando Servidor FastAPI em http://localhost:8000 ...")
    print("📊 Dashboard do TaskManager disponível em: http://localhost:8000/tasks/")
    uvicorn.run("samples.fastapi_sample.main:app", host="0.0.0.0", port=8000, reload=True)
