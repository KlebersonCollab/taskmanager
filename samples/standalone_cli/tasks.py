from __future__ import annotations

import asyncio
from typing import Any

from taskmanager import TaskContext, task


@task(name="cli_demo.export_analytics", queue="reports", max_retries=2)
async def export_analytics(date_str: str, ctx: TaskContext) -> dict[str, Any]:
    """Simulates background data extraction and CSV export with live streaming."""
    await ctx.append_log(f"📊 Extraindo dados analíticos para a data {date_str}...")
    await ctx.update_progress(25.0, "Consultando banco de dados")
    await asyncio.sleep(0.5)

    await ctx.append_log("Processando agregações e métricas de conversão...")
    await ctx.update_progress(70.0, "Gerando arquivo CSV")
    await asyncio.sleep(0.5)

    file_name = f"analytics_{date_str}.csv"
    await ctx.append_log(f"✅ Relatório '{file_name}' exportado com sucesso!")
    await ctx.update_progress(100.0, "Exportação concluída")
    return {"file": file_name, "records_processed": 1420}


@task(name="cli_demo.ping_healthcheck", queue="default")
def ping_healthcheck() -> str:
    """Synchronous CPU health check task."""
    return "ALL_SYSTEMS_OPERATIONAL"
