from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ExchangeSpec:
    name: str
    exchange_type: str = "direct"
    durable: bool = True
    auto_delete: bool = False


@dataclass(slots=True, frozen=True)
class QueueSpec:
    name: str
    durable: bool = True
    auto_delete: bool = False
    routing_key: str | None = None
