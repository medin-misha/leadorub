from typing import Any

from pydantic import BaseModel, Field

from .message import RMQMessage


class RMQPublishRequest(BaseModel):
    event: str = Field(min_length=1)
    payload: dict[str, Any]
    exchange_name: str | None = None
    queue_name: str | None = None
    routing_key: str | None = None
    source: str | None = None
    correlation_id: str | None = None
    exchange_type: str | None = None


class RMQPublishResponse(BaseModel):
    message: RMQMessage
    exchange_name: str | None = None
    queue_name: str | None = None
    routing_key: str
    source: str
    exchange_type: str | None = None


class RMQConsumeRequest(BaseModel):
    queue_name: str | None = None
    exchange_name: str | None = None
    routing_key: str | None = None
    exchange_type: str | None = None


class RMQConsumeResponse(BaseModel):
    status: str
    queue_name: str
    message: RMQMessage | None = None
    raw_body: str | None = None


class RMQRegistrationRead(BaseModel):
    queue_name: str
    exchange_name: str
    routing_key: str
    exchange_type: str
    handler_name: str
    auto_declare: bool


class RMQRuntimeHealth(BaseModel):
    enabled: bool
    configured: bool
    started: bool
    connected: bool
    consumer_enabled: bool
    registration_count: int
    listener_count: int
    default_exchange: str
    default_queue: str
