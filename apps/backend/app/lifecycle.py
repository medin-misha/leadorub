from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import settings
from app.core.database import database
from app.modules.rmq_module.runtime import shutdown_rmq_runtime, startup_rmq_runtime
from app.modules.taskiq_module import startup_taskiq_runtime, shutdown_taskiq_runtime


@asynccontextmanager
async def lifespan(_: FastAPI):
    await startup_taskiq_runtime()
    await startup_rmq_runtime()
    try:
        yield
    finally:
        await shutdown_taskiq_runtime()
        await shutdown_rmq_runtime()
        await database.dispose()
