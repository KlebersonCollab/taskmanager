"""
Exemplos de Tarefas do TaskManager (@task)
------------------------------------------------------------
Este módulo contém exemplos práticos de funções decoradas que
podem ser executadas por Workers em segundo plano ou agendadas via Cron.

Como iniciar o TaskManager carregando este módulo:
    uv run taskmanager dev --modules example_tasks
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any

from taskmanager import task


# ---------------------------------------------------------------------------
# 1. Tarefa Assíncrona: Envio de E-mail com Retentativas Automáticas
# ---------------------------------------------------------------------------
@task(
    name="emails.send_welcome_email",
    queue="emails",
    max_retries=3,
    retry_backoff=2.0,  # 2s, 4s, 8s (backoff exponencial)
    timeout=10.0,
)
async def send_welcome_email(email: str, name: str) -> dict[str, Any]:
    """Simula o envio assíncrono de e-mail de boas-vindas."""
    print(f"📧 [Email Worker] Enviando e-mail de boas-vindas para {name} <{email}>...")

    # Simula latência de rede (I/O)
    await asyncio.sleep(1.5)

    print(f"✅ [Email Worker] E-mail enviado com sucesso para {email}!")
    return {
        "status": "delivered",
        "recipient": email,
        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# 2. Tarefa Síncrona: Processamento de Relatório Financeiro / Vendas
# ---------------------------------------------------------------------------
@task(
    name="reports.generate_sales_report",
    queue="reports",
    max_retries=1,
    timeout=60.0,
)
def generate_sales_report(year: int, month: int, department: str = "Geral") -> dict[str, Any]:
    """Simula processamento síncrono pesado (ex: agregação de dados ou PDF)."""
    print(f"📊 [Report Worker] Gerando relatório {department} - {month:02d}/{year}...")

    # Simula computação de CPU
    total_sales = 0
    for i in range(1, 1001):
        total_sales += i * 15.5
    time.sleep(2.0)

    file_path = f"/exports/relatorio_{department.lower()}_{year}_{month:02d}.pdf"
    print(f"✅ [Report Worker] Relatório gerado em '{file_path}'!")
    return {
        "report_file": file_path,
        "total_revenue": round(total_sales, 2),
        "department": department,
        "period": f"{month:02d}/{year}",
    }


# ---------------------------------------------------------------------------
# 3. Tarefa Instável: Demonstração de Retentativas e Dead Letter Queue (DLQ)
# ---------------------------------------------------------------------------
@task(
    name="integrations.sync_payment_gateway",
    queue="payments",
    max_retries=2,
    retry_backoff=1.5,
    timeout=5.0,
)
async def sync_payment_gateway(order_id: str, force_fail: bool = False) -> dict[str, Any]:
    """Simula integração externa com gateway que pode falhar e ir para a DLQ."""
    print(f"💳 [Payment Worker] Sincronizando pedido #{order_id} com Gateway...")
    await asyncio.sleep(0.8)

    if force_fail or random.random() < 0.4:
        print(f"❌ [Payment Worker] Falha na comunicação com gateway para pedido #{order_id}!")
        raise ConnectionResetError(f"Gateway de pagamento indisponível para pedido {order_id}")

    print(f"✅ [Payment Worker] Pedido #{order_id} sincronizado!")
    return {"order_id": order_id, "status": "settled"}


# ---------------------------------------------------------------------------
# 4. Tarefa de Manutenção: Limpeza de Cache / Arquivos Temporários (Cron)
# ---------------------------------------------------------------------------
@task(
    name="system.cleanup_temp_files",
    queue="default",
    max_retries=1,
    timeout=30.0,
)
async def cleanup_temp_files(dry_run: bool = False) -> dict[str, Any]:
    """Rotina típica para ser agendada via Cron no Dashboard (ex: 0 * * * *)."""
    print(f"🧹 [Cleanup Worker] Iniciando varredura de arquivos temporários (dry_run={dry_run})...")
    await asyncio.sleep(1.0)

    deleted_count = 42 if not dry_run else 0
    freed_mb = 128.5 if not dry_run else 0.0

    print(f"✅ [Cleanup Worker] Limpeza concluída: {deleted_count} arquivos removidos ({freed_mb} MB liberados).")
    return {
        "deleted_files": deleted_count,
        "freed_mb": freed_mb,
        "dry_run": dry_run,
    }
