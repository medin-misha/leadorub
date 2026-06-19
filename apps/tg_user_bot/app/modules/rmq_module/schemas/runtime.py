from pydantic import BaseModel


class RMQRegistrationRead(BaseModel):
    queue_name: str
    exchange_name: str
    routing_key: str
    exchange_type: str
    handler_name: str
    auto_declare: bool


class RMQRuntimeHealth(BaseModel):
    started: bool
    connected: bool
    consumer_enabled: bool
    registration_count: int
    listener_count: int
    should_start: bool
    default_exchange: str
    default_queue: str
