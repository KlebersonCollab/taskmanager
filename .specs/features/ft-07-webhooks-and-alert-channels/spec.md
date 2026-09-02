# Specification: Webhooks & Multi-Platform Alert Channels (ft-07)

## 1. User Stories
- **US-1**: As a developer/DevOps engineer, I want to configure Slack, Discord, Microsoft Teams, Telegram, and generic Webhook channels, so that my team is instantly notified when a task fails permanently and enters the DLQ.
- **US-2**: As an administrator, I want to send a test alert from the UI to any configured channel, so that I can verify webhook URLs and credentials before relying on them in production.
- **US-3**: As a security-conscious engineer, I want generic webhooks to support secret authorization headers, so that my receiving endpoint can authenticate requests.

## 2. Business Rules & Invariants
- **BR-1**: Alert dispatching must be non-blocking and fail-safe; if an external alert endpoint is down or returns an HTTP error, it must log the warning without disrupting or failing the background worker or job lifecycle.
- **BR-2**: Alert payloads must be properly formatted according to each platform's API expectations:
  - **Slack**: JSON with `text` or `attachments` (color `#ef4444`).
  - **Discord**: JSON with `embeds` array and integer color codes.
  - **Teams**: JSON with `title`, `text`, or Adaptive Card structure.
  - **Telegram**: Form-encoded or JSON with `chat_id` and formatted `text`.
  - **Generic Webhook**: JSON with event payload, plus optional `Authorization` or `X-Webhook-Secret` header.
- **BR-3**: Only enabled channels matching the triggered event (e.g. `job:failed`) must receive the alert.
- **BR-4**: All channel configurations must be persisted in Redis hash `tm:alerts:channels`.

## 3. Acceptance Criteria (BDD)

### Happy Path (Success Scenarios)
- **AC-1: Channel Creation & Persistence**
  - **Given** valid alert channel parameters (name, channel_type, target_url, events)
  - **When** `POST /api/alerts/channels` is called
  - **Then** the channel is saved in Redis and returned with a unique ID and `created_at` timestamp.

- **AC-2: Multi-Platform Payload Formatting**
  - **Given** a `job:failed` event with task name, queue, job ID, and error message
  - **When** the alert dispatcher formats the event for Slack, Discord, Teams, Telegram, and Webhook
  - **Then** each platform produces its respective valid payload schema with job details included.

- **AC-3: Automated DLQ Failure Triggering**
  - **Given** an enabled Slack alert channel subscribed to `job:failed`
  - **When** a job fails and exhausts its retries in `broker.mark_failed(job)`
  - **Then** the broker dispatches the alert to the configured Slack webhook URL.

- **AC-4: Test Alert Ping**
  - **Given** a configured alert channel
  - **When** `POST /api/alerts/channels/{id}/test` is called
  - **Then** a test payload is dispatched to the channel and the HTTP response status is returned.

### Input & Validation Scenarios
- **AC-5: Invalid Channel Validation**
  - **Given** a payload missing required target URL or with an unsupported channel type
  - **When** creating the channel via API
  - **Then** the API returns HTTP 422/400 validation error.

### Edge Cases & Exceptions (Resilience)
- **AC-6: External Webhook Network Timeout / Failure**
  - **Given** a configured webhook URL that is unreachable or times out
  - **When** an alert is dispatched
  - **Then** the dispatcher handles the exception gracefully without raising unhandled errors to the worker loop.

## 4. Test Data & Matrix
| Platform | Target URL / Identifier | Expected Payload Root Keys |
|---|---|---|
| `slack` | `https://hooks.slack.com/services/...` | `text`, `attachments` |
| `discord` | `https://discord.com/api/webhooks/...` | `embeds` |
| `teams` | `https://outlook.office.com/webhook/...` | `title`, `text` |
| `telegram` | `https://api.telegram.org/bot<token>/sendMessage` | `chat_id`, `text`, `parse_mode` |
| `webhook` | `https://api.example.com/webhooks/tasks` | `event`, `timestamp`, `data` |

## 5. Verification Sensors
| Sensor | Command / Target | Success Threshold |
|---|---|---|
| Linter | `uv run ruff check taskmanager tests` | 0 errors |
| Test Suite | `uv run pytest` | 100% pass |
| Spec Drift | `node .agents/scripts/check-spec-drift.js` | 0 drift violations |
