from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings
from app.core.database import database

router = APIRouter(prefix="/system", tags=["system"])


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


@router.get("/health")
async def application_health_check() -> dict[str, object]:
    return {
        "status": "ok",
        "service": settings.project_name,
        "timestamp": _utc_timestamp(),
        "checks": {
            "application": {
                "status": "ok",
            }
        },
    }


@router.get("/health/db")
async def database_health_check(
    session: AsyncSession = Depends(database.get_session),
) -> dict[str, object]:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "service": settings.project_name,
                "timestamp": _utc_timestamp(),
                "checks": {
                    "database": {
                        "status": "error",
                        "message": "Database is unavailable.",
                        "error_type": err.__class__.__name__,
                    }
                },
            },
        ) from err

    return {
        "status": "ok",
        "service": settings.project_name,
        "timestamp": _utc_timestamp(),
        "checks": {
            "database": {
                "status": "ok",
                "message": "Database connection is available.",
            }
        },
    }
