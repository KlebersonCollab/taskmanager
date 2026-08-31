from __future__ import annotations

import asyncio
from typing import Any

from taskmanager import task


@task(name="cli_demo.export_analytics", queue="reports", max_retries=2)
async def export_analytics(date_str: str) -> dict[str, Any]:
    """Simulates background data extraction and CSV export."""
    print(f"📊 [Analytics Task] Extraindo dados analíticos para a data {date_str}...")
    await asyncio.sleep(2.0)
    file_name = f"analytics_{date_str}.csv"
    print(f"✅ [Analytics Task] Relatório '{file_name}' exportado com sucesso!")
    return {"file": file_name, "records_processed": 1420}


@task(name="cli_demo.ping_healthcheck", queue="default")
def ping_healthcheck() -> str:
    """Synchronous CPU health check task."""
    print("💓 [Health Task] Verificando integridade dos serviços...")
    return "ALL_SYSTEMS_OPERATIONAL"
