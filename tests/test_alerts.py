from unittest.mock import AsyncMock, patch

import pytest

from taskmanager.alerts.channel import AlertChannel, ChannelType
from taskmanager.alerts.dispatcher import AlertDispatcher, format_alert_payload
from taskmanager.core.broker import RedisBroker
from taskmanager.core.job import Job


def test_alert_channel_model_creation():
    channel = AlertChannel(
        name="Slack Ops",
        channel_type=ChannelType.SLACK,
        target_url="https://hooks.slack.com/services/test",
        events=["job:failed"],
    )
    assert channel.id is not None
    assert channel.name == "Slack Ops"
    assert channel.channel_type == ChannelType.SLACK
    assert channel.enabled is True
    assert "job:failed" in channel.events


def test_format_alert_payload_multi_platform():
    event_data = {
        "job_id": "job-12345678-abcd",
        "task_name": "payments.process",
        "queue": "payments",
        "error": "CardExpiredException: Card expired",
        "retry_count": 3,
        "max_retries": 3,
    }

    # 1. Slack format
    slack_ch = AlertChannel(
        name="Slack",
        channel_type=ChannelType.SLACK,
        target_url="https://hooks.slack.com/test",
    )
    slack_payload = format_alert_payload(slack_ch, "job:failed", event_data)
    assert "text" in slack_payload or "attachments" in slack_payload
    assert "payments.process" in str(slack_payload)

    # 2. Discord format
    discord_ch = AlertChannel(
        name="Discord",
        channel_type=ChannelType.DISCORD,
        target_url="https://discord.com/api/webhooks/test",
    )
    discord_payload = format_alert_payload(discord_ch, "job:failed", event_data)
    assert "embeds" in discord_payload
    assert len(discord_payload["embeds"]) > 0
    assert "CardExpiredException" in discord_payload["embeds"][0]["description"]

    # 3. Teams format
    teams_ch = AlertChannel(
        name="Teams",
        channel_type=ChannelType.TEAMS,
        target_url="https://outlook.office.com/webhook/test",
    )
    teams_payload = format_alert_payload(teams_ch, "job:failed", event_data)
    assert "title" in teams_payload or "text" in teams_payload
    assert "payments.process" in str(teams_payload)

    # 4. Telegram format
    telegram_ch = AlertChannel(
        name="Telegram",
        channel_type=ChannelType.TELEGRAM,
        target_url="https://api.telegram.org/bot123:TOKEN/sendMessage",
        telegram_chat_id="-10012345678",
    )
    telegram_payload = format_alert_payload(telegram_ch, "job:failed", event_data)
    assert telegram_payload["chat_id"] == "-10012345678"
    assert "payments.process" in telegram_payload["text"]

    # 5. Generic Webhook format
    webhook_ch = AlertChannel(
        name="Webhook",
        channel_type=ChannelType.WEBHOOK,
        target_url="https://api.example.com/alerts",
        secret_token="secret-123",
    )
    webhook_payload = format_alert_payload(webhook_ch, "job:failed", event_data)
    assert webhook_payload["event"] == "job:failed"
    assert webhook_payload["data"]["job_id"] == "job-12345678-abcd"


@pytest.mark.asyncio
async def test_alert_dispatcher_send_success():
    channel = AlertChannel(
        name="Slack Channel",
        channel_type=ChannelType.SLACK,
        target_url="https://hooks.slack.com/test",
    )
    dispatcher = AlertDispatcher()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.is_success = True

        result = await dispatcher.send_alert(
            channel,
            "job:failed",
            {"job_id": "j1", "task_name": "test_task", "error": "Crash"},
        )
        assert result["success"] is True
        assert result["status_code"] == 200
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_broker_alert_channels_crud_and_auto_trigger(fake_redis):
    broker = RedisBroker(fake_redis, prefix="test_alerts_tm")

    # 1. Save alert channel
    channel = AlertChannel(
        name="Discord Alerts",
        channel_type=ChannelType.DISCORD,
        target_url="https://discord.com/api/webhooks/test",
        events=["job:failed"],
    )
    await broker.save_alert_channel(channel)

    # 2. List channels
    channels = await broker.list_alert_channels()
    assert len(channels) == 1
    assert channels[0].id == channel.id
    assert channels[0].name == "Discord Alerts"

    # 3. Get channel by ID
    fetched = await broker.get_alert_channel(channel.id)
    assert fetched is not None
    assert fetched.name == "Discord Alerts"

    # 4. Trigger alert on job failure (mark_failed)
    job = Job(
        task_name="failing_task",
        queue="default",
        max_retries=0,
        retry_count=0,
    )
    await broker.save_job(job)

    with patch.object(broker.alert_dispatcher, "send_alert", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True, "status_code": 200}
        await broker.mark_failed(job, error="FatalDatabaseError")

        # Verify alert was dispatched
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        assert args[0].id == channel.id
        assert args[1] == "job:failed"
        assert args[2]["error"] == "FatalDatabaseError"

    # 5. Delete channel
    deleted = await broker.delete_alert_channel(channel.id)
    assert deleted is True
    channels_after = await broker.list_alert_channels()
    assert len(channels_after) == 0
