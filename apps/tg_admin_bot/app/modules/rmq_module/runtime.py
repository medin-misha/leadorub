"""
Lifecycle hooks for the RMQ system infrastructure module.

These thin wrappers are called by `app.bot.lifecycle` on startup and shutdown.
They exist to keep the public API surface of rmq_module explicit and stable.
"""

from __future__ import annotations

from app.core import MainSettings

from .services import rmq_runtime


async def startup_rmq_runtime(_: MainSettings | None = None) -> None:
    """Starts the shared RabbitMQ runtime explicitly."""

    await rmq_runtime.start()


async def shutdown_rmq_runtime() -> None:
    """Stops the shared RabbitMQ runtime explicitly."""

    await rmq_runtime.stop()
