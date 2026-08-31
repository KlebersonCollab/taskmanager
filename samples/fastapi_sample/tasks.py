from __future__ import annotations

import asyncio
from typing import Any

from taskmanager import task


@task(name="notifications.send_email", queue="emails", max_retries=3, retry_backoff=2.0)
async def send_email(recipient: str, subject: str, body: str) -> dict[str, Any]:
    """Simulates sending an email asynchronously."""
    print(f"📧 [Email Worker] Enviando e-mail para '{recipient}' com assunto '{subject}'...")
    await asyncio.sleep(1.0)
    print(f"✅ [Email Worker] E-mail entregue com sucesso para '{recipient}'!")
    return {"recipient": recipient, "status": "sent"}


@task(name="orders.process_checkout", queue="orders", max_retries=2)
async def process_checkout(order_id: str, amount: float) -> dict[str, Any]:
    """Simulates processing an e-commerce checkout."""
    print(f"💳 [Order Worker] Processando pedido #{order_id} no valor de R$ {amount:.2f}...")
    await asyncio.sleep(1.5)
    print(f"✅ [Order Worker] Pedido #{order_id} faturado com sucesso!")
    return {"order_id": order_id, "amount": amount, "status": "settled"}
