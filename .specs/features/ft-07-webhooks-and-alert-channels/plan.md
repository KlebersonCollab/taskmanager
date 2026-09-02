# Plan: Webhooks & Multi-Platform Alert Channels (ft-07)

## 1. Problem Statement & Motivation
When background jobs fail or get routed to the Dead Letter Queue (DLQ), engineering and operations teams need immediate notifications in their team communication platforms (Slack, Discord, Microsoft Teams, Telegram) or automated incident management systems via generic HTTP Webhooks.

Currently, failure information is only visible within the dashboard. This feature adds a multi-platform alert notification engine that triggers formatted alerts whenever critical events occur (such as job failure after all retries or worker down), with zero external monitoring stack requirements.

## 2. Scope & Boundaries
- **In Scope**:
  - `AlertChannel` data model supporting 5 channel types: `slack`, `discord`, `teams`, `telegram`, and `webhook`.
  - Formatters customized for each platform:
    - **Slack**: Webhook payload with attachments, color accents, and job details.
    - **Discord**: Webhook payload with rich embeds and error traceback snippets.
    - **Microsoft Teams**: Connector/Adaptive card format with key-value facts and color tags.
    - **Telegram**: Bot API message dispatcher with markdown formatting and chat ID routing.
    - **Generic Webhook**: Standard JSON payload with custom secret headers/tokens.
  - Redis persistence for configured alert channels in `RedisBroker` (`tm:alerts:channels`).
  - Automatic event-driven dispatching upon `job:failed` (DLQ routing) and worker disconnects.
  - REST API for Alert Channels CRUD (`GET`, `POST`, `PUT`, `DELETE`, `POST /test`).
  - Interactive UI modal and management screen in the Linear Dark Dashboard.
- **Out of Scope**:
  - Bidirectional Slack bot slash command interactive dialogs (focused on outbound alerting).
  - SMS/PSTN telephony gateways (Twilio/PagerDuty can be integrated via generic Webhook).

## 3. High-Level Approach
1. **Model Layer**: Create `taskmanager/alerts/channel.py` defining `AlertChannel` and `ChannelType`.
2. **Dispatcher Engine**: Create `taskmanager/alerts/dispatcher.py` with platform-specific payload formatters and non-blocking asynchronous HTTP dispatching.
3. **Broker Integration**: Implement `save_alert_channel`, `get_alert_channel`, `list_alert_channels`, `delete_alert_channel`, and auto-trigger in `mark_failed` in `taskmanager/core/broker.py`.
4. **API Endpoints**: Add `/api/alerts/channels` CRUD and `/api/alerts/channels/{id}/test` in `taskmanager/api/app.py`.
5. **Dashboard UI**: Add Alert Channels management modal, test ping trigger, and platform badge renderers in `index.html`, `styles.css`, and `app.js`.

## 4. Dependencies & Prerequisites
- Python `httpx` or `asyncio` / standard library for outbound webhook delivery.
- Redis storage for alert channel configuration.
