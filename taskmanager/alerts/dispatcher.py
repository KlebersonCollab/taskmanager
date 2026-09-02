import html
import logging
import time
from typing import Any

import httpx

from taskmanager.alerts.channel import AlertChannel, ChannelType

logger = logging.getLogger("taskmanager.alerts")


def format_alert_payload(
    channel: AlertChannel, event_type: str, event_data: dict[str, Any]
) -> dict[str, Any]:
    """Formats an event into a platform-specific webhook payload."""
    job_id = event_data.get("job_id", "--")
    task_name = event_data.get("task_name", event_data.get("task", "--"))
    queue = event_data.get("queue", "default")
    error = event_data.get("error", "No error message specified")
    retry_count = event_data.get("retry_count", 0)
    max_retries = event_data.get("max_retries", 0)
    worker_id = event_data.get("worker_id", "--")

    if channel.channel_type == ChannelType.SLACK:
        return {
            "text": f"🚨 *TaskManager Alert* — `{event_type}` in queue `{queue}`",
            "attachments": [
                {
                    "color": "#ef4444" if "fail" in event_type else "#5e6ad2",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*Task:* `{task_name}`\n"
                                    f"*Job ID:* `{job_id}`\n"
                                    f"*Queue:* `{queue}`\n"
                                    f"*Error:* ```{error}```"
                                ),
                            },
                        }
                    ],
                }
            ],
        }

    elif channel.channel_type == ChannelType.DISCORD:
        return {
            "content": f"🚨 **TaskManager Alert** — `{event_type}`",
            "embeds": [
                {
                    "title": f"Task Alert: {task_name}",
                    "description": f"**Queue:** `{queue}`\n**Job ID:** `{job_id}`\n**Error:** ```{error}```",
                    "color": 15673668,  # #ef4444
                    "fields": [
                        {"name": "Retries", "value": f"{retry_count}/{max_retries}", "inline": True},
                        {"name": "Worker", "value": f"{worker_id or '--'}", "inline": True},
                    ],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            ],
        }

    elif channel.channel_type == ChannelType.TEAMS:
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "ef4444" if "fail" in event_type else "5e6ad2",
            "summary": f"TaskManager Alert: {task_name}",
            "title": f"🚨 TaskManager Alert: {task_name}",
            "text": (
                f"**Event:** `{event_type}`\n\n"
                f"**Task:** `{task_name}`\n\n"
                f"**Queue:** `{queue}`\n\n"
                f"**Job ID:** `{job_id}`\n\n"
                f"**Error:** `{error}`"
            ),
        }

    elif channel.channel_type == ChannelType.TELEGRAM:
        chat_id = channel.telegram_chat_id or ""
        safe_task = html.escape(str(task_name))
        safe_queue = html.escape(str(queue))
        safe_job = html.escape(str(job_id))
        safe_err = html.escape(str(error))
        safe_event = html.escape(str(event_type))

        text = (
            f"🚨 <b>TaskManager Alert</b>\n\n"
            f"<b>Evento:</b> <code>{safe_event}</code>\n"
            f"<b>Tarefa:</b> <code>{safe_task}</code>\n"
            f"<b>Fila:</b> <code>{safe_queue}</code>\n"
            f"<b>Job ID:</b> <code>{safe_job}</code>\n"
            f"<b>Erro:</b> <pre>{safe_err}</pre>"
        )
        return {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

    else:
        # Default / Generic Webhook
        return {
            "event": event_type,
            "timestamp": time.time(),
            "channel_id": channel.id,
            "channel_name": channel.name,
            "data": event_data,
        }


def resolve_channel_url(channel: AlertChannel) -> str:
    """Normalizes the target URL, auto-formatting Telegram bot token URLs if needed."""
    url = (channel.target_url or "").strip()
    if channel.channel_type == ChannelType.TELEGRAM:
        if not url.startswith("http://") and not url.startswith("https://"):
            if url.startswith("bot"):
                return f"https://api.telegram.org/{url}/sendMessage"
            return f"https://api.telegram.org/bot{url}/sendMessage"
        if "api.telegram.org" in url and not url.endswith("/sendMessage"):
            return f"{url.rstrip('/')}/sendMessage"
    return url


class AlertDispatcher:
    """Asynchronous HTTP dispatcher for delivering alert notifications."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def send_alert(
        self, channel: AlertChannel, event_type: str, event_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatches an alert to the channel's target URL in a fail-safe manner."""
        target_url = resolve_channel_url(channel)
        payload = format_alert_payload(channel, event_type, event_data)
        headers = {"Content-Type": "application/json", "User-Agent": "TaskManager-Alerts/1.0"}

        if channel.secret_token:
            headers["X-Webhook-Secret"] = channel.secret_token
            headers["Authorization"] = f"Bearer {channel.secret_token}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(target_url, json=payload, headers=headers)
                success = res.is_success
                err_detail = None

                if not success:
                    try:
                        res_json = res.json()
                        err_detail = res_json.get("description") or res_json.get("message") or res.text[:300]
                    except Exception:
                        err_detail = res.text[:300]

                return {
                    "success": success,
                    "status_code": res.status_code,
                    "error": f"HTTP {res.status_code}: {err_detail}" if err_detail else None,
                    "response_text": res.text[:500],
                }
        except Exception as err:
            logger.warning(f"Failed to dispatch alert to channel {channel.name} ({channel.id}): {err}")
            return {
                "success": False,
                "error": str(err),
            }

