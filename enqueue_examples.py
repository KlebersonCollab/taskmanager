"""
Script de Demonstração: Enfileirando Tarefas Programaticamente
------------------------------------------------------------
Este script demonstra como disparar tarefas diretamente no código Python
utilizando os métodos `.delay()` e `.apply_async()`.

Para executar:
    uv run python enqueue_examples.py
"""

from __future__ import annotations

import asyncio

from example_tasks import (
    cleanup_temp_files,
    generate_sales_report,
    send_welcome_email,
    sync_payment_gateway,
)
from taskmanager.cli import get_redis_client
from taskmanager.config import settings
from taskmanager.core.broker import RedisBroker
from taskmanager.core.task import registry


async def main() -> None:
    print("🚀 Conectando ao Broker do TaskManager...")

    # 1. Inicializa o broker conectado ao Redis
    client = await get_redis_client(settings.redis_url)
    broker = RedisBroker(client, prefix=settings.redis_prefix)
    registry.set_broker(broker)

    print("\n--- 1. Enfileirando E-mail Imediato (.delay) ---")
    job_email = await send_welcome_email.delay(
        email="cliente.vip@empresa.com",
        name="Carlos Silva",
    )
    print(f"✅ Job de e-mail criado: ID={job_email.id} (Fila: {job_email.queue})")

    print("\n--- 2. Enfileirando Relatório de Vendas (.delay) ---")
    job_report = await generate_sales_report.delay(
        year=2026,
        month=8,
        department="Financeiro",
    )
    print(f"✅ Job de relatório criado: ID={job_report.id} (Fila: {job_report.queue})")

    print("\n--- 3. Enfileirando Tarefa Agendada com Delay de 10s (.apply_async) ---")
    job_delayed = await cleanup_temp_files.apply_async(
        kwargs={"dry_run": False},
        delay=10.0,  # Executará somente após 10 segundos
    )
    print(f"⏰ Job agendado criado: ID={job_delayed.id} (Status: {job_delayed.status})")

    print("\n--- 4. Enfileirando Pagamento com Simulação de Falha (DLQ) ---")
    job_payment = await sync_payment_gateway.delay(
        order_id="PED-98765",
        force_fail=True,  # Força falhas sucessivas para demonstrar a Dead Letter Queue
    )
    print(f"⚡ Job de pagamento com falha forçada: ID={job_payment.id}")

    print("\n🎉 Todas as tarefas de exemplo foram enviadas para as filas do Redis!")
    print("👉 Abra o Dashboard em http://localhost:8000 para acompanhar a execução em tempo real!")


if __name__ == "__main__":
    asyncio.run(main())
