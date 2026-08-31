from __future__ import annotations

import asyncio
from typing import Any

from taskmanager import task


@task(name="django_app.generate_monthly_invoices", queue="billing", max_retries=2)
async def generate_monthly_invoices(month: int, year: int) -> dict[str, Any]:
    """Simula faturamento e emissão de notas fiscais de clientes Django."""
    print(f"💰 [Django Billing Worker] Gerando faturas de {month:02d}/{year}...")
    await asyncio.sleep(1.2)
    print("✅ [Django Billing Worker] Faturas geradas com sucesso!")
    return {"month": month, "year": year, "invoices_generated": 150}


@task(name="django_app.sync_user_avatar", queue="default")
async def sync_user_avatar(user_id: int) -> dict[str, Any]:
    """Simula redimensionamento assíncrono de imagem de perfil."""
    print(f"🖼️ [Django Worker] Processando avatar para o usuário #{user_id}...")
    await asyncio.sleep(0.8)
    return {"user_id": user_id, "avatar_url": f"https://cdn.exemplo.com/avatars/{user_id}.webp"}
