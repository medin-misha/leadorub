from fastapi import APIRouter, HTTPException, status

from .config import rmq_settings
from .schemas import (
    RMQConsumeRequest,
    RMQConsumeResponse,
    RMQPublishRequest,
    RMQPublishResponse,
    RMQRegistrationRead,
    RMQRuntimeHealth,
)
from .services import rmq_client, rmq_publisher, rmq_registry, rmq_runtime

router = APIRouter(prefix="/rmq", tags=["rmq"])


def _ensure_debug_endpoints_enabled() -> None:
    if rmq_settings.debug_endpoints_enabled:
        return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="RabbitMQ debug endpoints are disabled.",
    )


@router.get("/health", response_model=RMQRuntimeHealth)
async def rmq_health() -> RMQRuntimeHealth:
    return RMQRuntimeHealth.model_validate(rmq_runtime.describe())


@router.get("/registrations", response_model=list[RMQRegistrationRead])
async def list_rmq_registrations() -> list[RMQRegistrationRead]:
    return [
        RMQRegistrationRead.model_validate(item) for item in rmq_registry.describe()
    ]


@router.post("/publish", response_model=RMQPublishResponse)
async def publish_rmq_message(data: RMQPublishRequest) -> RMQPublishResponse:
    _ensure_debug_endpoints_enabled()
    message = await rmq_publisher.publish(
        event=data.event,
        payload=data.payload,
        exchange_name=data.exchange_name,
        routing_key=data.routing_key,
        queue_name=data.queue_name,
        source=data.source,
        correlation_id=data.correlation_id,
        exchange_type=data.exchange_type,
    )
    return RMQPublishResponse(
        message=message,
        exchange_name=data.exchange_name,
        queue_name=data.queue_name,
        routing_key=data.routing_key
        or data.queue_name
        or rmq_publisher.default_routing_key,
        source=message.source,
        exchange_type=data.exchange_type,
    )


@router.post("/consume", response_model=RMQConsumeResponse)
async def consume_rmq_message(data: RMQConsumeRequest) -> RMQConsumeResponse:
    _ensure_debug_endpoints_enabled()
    queue_name = data.queue_name or rmq_publisher.default_queue_name
    await rmq_runtime.ensure_topology(
        exchange_name=data.exchange_name,
        queue_name=queue_name,
        routing_key=data.routing_key or queue_name,
        exchange_type=data.exchange_type,
    )
    incoming = await rmq_client.get_message(queue_name=queue_name)
    if incoming is None:
        return RMQConsumeResponse(status="empty", queue_name=queue_name)

    raw_body = incoming.body.decode("utf-8", errors="replace")
    message = rmq_runtime.parse_message(incoming.body)
    await incoming.ack()

    return RMQConsumeResponse(
        status="consumed",
        queue_name=queue_name,
        message=message,
        raw_body=None if message is not None else raw_body,
    )
