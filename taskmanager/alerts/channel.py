import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"


class AlertChannel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    channel_type: ChannelType
    target_url: str
    telegram_chat_id: str | None = None
    secret_token: str | None = None
    events: list[str] = Field(default_factory=lambda: ["job:failed"])
    enabled: bool = True
    created_at: float = Field(default_factory=time.time)

    def matches_event(self, event_type: str) -> bool:
        """Checks if this channel is enabled and subscribed to the event type."""
        if not self.enabled:
            return False
        return event_type in self.events or "*" in self.events
