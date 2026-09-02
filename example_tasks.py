"""
Exemplos de Tarefas do TaskManager (@task)
------------------------------------------------------------
Este módulo contém exemplos práticos de funções decoradas demonstrando:
- Progresso em tempo real e streaming de logs (TaskContext)
- Rate limiting por segundo/minuto (Token Bucket em Redis)
- Concorrência máxima por tarefa (Distributed Semaphore)
- Retentativas automáticas e Dead Letter Queue (DLQ)

Como iniciar o TaskManager carregando este módulo:
    uv run taskmanager dev --modules example_tasks
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any

from taskmanager import TaskContext, task


# ---------------------------------------------------------------------------
# 1. Tarefa com Progresso em Tempo Real & Live Log Streaming
# ---------------------------------------------------------------------------
@task(
    name="emails.send_welcome_email",
    queue="emails",
    max_retries=3,
    retry_backoff=2.0,  # 2s, 4s, 8s (backoff exponencial)
    timeout=10.0,
)
async def send_welcome_email(email: str, name: str, ctx: TaskContext) -> dict[str, Any]:
    """Simula o envio assíncrono de e-mail com atualização de progresso e logs."""
    await ctx.append_log(f"Iniciando envio de e-mail para {name} <{email}>...")
    await ctx.update_progress(20.0, "Validando formato de e-mail e DNS")
    await asyncio.sleep(0.5)

    await ctx.append_log("Conectando ao servidor SMTP transacional...")
    await ctx.update_progress(60.0, "Transmitindo corpo HTML e anexos")
    await asyncio.sleep(0.6)

    await ctx.append_log(f"✅ E-mail entregue com sucesso para {email}!")
    await ctx.update_progress(100.0, "Entregue")
    return {
        "status": "delivered",
        "recipient": email,
        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# 2. Tarefa com Rate Limiting (Token Bucket: Máx 5 requisições por segundo)
# ---------------------------------------------------------------------------
@task(
    name="whatsapp.send_message",
    queue="messaging",
    rate_limit="5/s",  # Limita rigorosamente a vazão para APIs externas
    max_retries=2,
)
async def send_whatsapp_message(phone: str, text: str, ctx: TaskContext) -> dict[str, Any]:
    """Demonstra Rate Limiting em Redis para evitar HTTP 429 Too Many Requests."""
    await ctx.append_log(f"Disparando mensagem WhatsApp para {phone}...")
    await ctx.update_progress(50.0, "Rate limit verificado no Redis")
    await asyncio.sleep(0.3)

    await ctx.append_log(f"Mensagem entregue ao destinatário: '{text[:30]}...'")
    await ctx.update_progress(100.0, "Mensagem enviada")
    return {"phone": phone, "status": "sent", "timestamp": time.time()}


# ---------------------------------------------------------------------------
# 3. Tarefa com Concorrência Máxima (Distributed Semaphore: Máx 2 simultâneas)
# ---------------------------------------------------------------------------
@task(
    name="reports.heavy_export",
    queue="reports",
    max_concurrency=2,  # No cluster inteiro, no máximo 2 instâncias desta task rodam ao mesmo tempo
    max_retries=1,
    timeout=60.0,
)
async def heavy_export(year: int, month: int, department: str = "Financeiro", ctx: TaskContext | None = None) -> dict[str, Any]:
    """Demonstra trava de concorrência máxima para proteger CPU e conexões de banco."""
    if ctx:
        await ctx.append_log(f"Iniciando exportação analítica de {department} ({month:02d}/{year})...")
        await ctx.update_progress(10.0, "Slot de concorrência adquirido")

    # Simula etapas de processamento
    for step in range(1, 6):
        await asyncio.sleep(0.4)
        if ctx:
            pct = round((step / 5) * 100, 1)
            await ctx.update_progress(pct, f"Processando lote {step} de 5")
            await ctx.append_log(f"Lote {step} de dados consolidados com sucesso.")

    file_path = f"/exports/relatorio_{department.lower()}_{year}_{month:02d}.xlsx"
    if ctx:
        await ctx.append_log(f"✅ Arquivo final gerado em '{file_path}'")
        await ctx.update_progress(100.0, "Concluído")

    return {
        "report_file": file_path,
        "department": department,
        "period": f"{month:02d}/{year}",
    }


# ---------------------------------------------------------------------------
# 4. Tarefa Instável: Demonstração de Retentativas e Dead Letter Queue (DLQ)
# ---------------------------------------------------------------------------
@task(
    name="integrations.sync_payment_gateway",
    queue="payments",
    max_retries=2,
    retry_backoff=1.5,
    timeout=5.0,
)
async def sync_payment_gateway(order_id: str, force_fail: bool = False, ctx: TaskContext | None = None) -> dict[str, Any]:
    """Simula integração que pode falhar, esgotar retentativas e disparar alerta na DLQ."""
    if ctx:
        await ctx.append_log(f"Iniciando comunicação com Gateway de Pagamento para pedido #{order_id}...")

    await asyncio.sleep(0.5)

    if force_fail or random.random() < 0.3:
        if ctx:
            await ctx.append_log(f"❌ Erro 503 Service Unavailable no Gateway para pedido #{order_id}")
        raise ConnectionResetError(f"Gateway de pagamento indisponível para pedido {order_id}")

    if ctx:
        await ctx.append_log(f"✅ Pagamento confirmado para pedido #{order_id}")
        await ctx.update_progress(100.0, "Faturado")

    return {"order_id": order_id, "status": "settled"}


# ---------------------------------------------------------------------------
# 5. Tarefa Síncrona CPU-Bound: Healthcheck Rápido
# ---------------------------------------------------------------------------
@task(
    name="system.ping_healthcheck",
    queue="default",
    max_retries=1,
)
def ping_healthcheck() -> str:
    """Função síncrona simples (def) executada em threadpool pelo worker asyncio."""
    return "ALL_SYSTEMS_OPERATIONAL"
