from __future__ import annotations

import asyncio
from typing import Any

from taskmanager import TaskContext, task


@task(name="django_app.generate_monthly_invoices", queue="billing", max_retries=2)
async def generate_monthly_invoices(month: int, year: int, ctx: TaskContext) -> dict[str, Any]:
    """Simula faturamento e emissão de notas fiscais de clientes Django com logs ao vivo."""
    await ctx.append_log(f"Iniciando cálculo de faturamento para competência {month:02d}/{year}...")
    await ctx.update_progress(20.0, "Consultando assinaturas ativas")
    await asyncio.sleep(0.4)

    await ctx.append_log("Gerando arquivos PDF das faturas...")
    await ctx.update_progress(70.0, "Gerando PDFs e boletos")
    await asyncio.sleep(0.5)

    await ctx.append_log("Faturas e notas fiscais geradas com sucesso!")
    await ctx.update_progress(100.0, "Concluído")
    return {"month": month, "year": year, "invoices_generated": 150}


@task(name="django_app.sync_user_avatar", queue="default")
async def sync_user_avatar(user_id: int, ctx: TaskContext) -> dict[str, Any]:
    """Simula redimensionamento assíncrono de imagem de perfil com progresso."""
    await ctx.append_log(f"Baixando imagem original do usuário #{user_id}...")
    await ctx.update_progress(30.0, "Download da imagem")
    await asyncio.sleep(0.3)

    await ctx.append_log("Otimizando e gerando variantes WebP (64x64, 128x128, 256x256)...")
    await ctx.update_progress(80.0, "Convertendo para WebP")
    await asyncio.sleep(0.3)

    await ctx.append_log("Upload concluído para o CDN!")
    await ctx.update_progress(100.0, "Avatar sincronizado")
    return {"user_id": user_id, "avatar_url": f"https://cdn.exemplo.com/avatars/{user_id}.webp"}
