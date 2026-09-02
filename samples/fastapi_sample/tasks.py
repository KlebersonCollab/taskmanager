from __future__ import annotations

import asyncio
from typing import Any

from taskmanager import TaskContext, task


@task(name="notifications.send_email", queue="emails", max_retries=3, retry_backoff=2.0)
async def send_email(recipient: str, subject: str, body: str, ctx: TaskContext) -> dict[str, Any]:
    """Simulates sending an email asynchronously with live progress."""
    await ctx.append_log(f"Conectando ao servidor SMTP para {recipient}...")
    await ctx.update_progress(30.0, "Conectado ao SMTP")
    await asyncio.sleep(0.5)

    await ctx.append_log(f"Enviando payload com assunto '{subject}'...")
    await ctx.update_progress(80.0, "Transmitindo mensagem...")
    await asyncio.sleep(0.5)

    await ctx.append_log(f"✅ E-mail entregue com sucesso para '{recipient}'!")
    await ctx.update_progress(100.0, "Entregue")
    return {"recipient": recipient, "status": "sent"}


@task(name="orders.process_checkout", queue="orders", max_retries=2)
async def process_checkout(order_id: str, amount: float, ctx: TaskContext) -> dict[str, Any]:
    """Simulates processing an e-commerce checkout with live progress."""
    await ctx.append_log(f"Iniciando checkout do pedido #{order_id} (R$ {amount:.2f})...")
    await ctx.update_progress(25.0, "Validando antifraude")
    await asyncio.sleep(0.5)

    await ctx.append_log("Antifraude aprovado. Cobrando cartão de crédito...")
    await ctx.update_progress(60.0, "Cobrança efetuada")
    await asyncio.sleep(0.5)

    await ctx.append_log("Gerando nota fiscal e liberando estoque...")
    await ctx.update_progress(90.0, "Nota fiscal emitida")
    await asyncio.sleep(0.4)

    await ctx.append_log(f"✅ Pedido #{order_id} concluído com sucesso!")
    return {"order_id": order_id, "amount": amount, "status": "settled"}
