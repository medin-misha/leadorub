import logging
import traceback
from typing import Type, TypeVar
from fastapi import HTTPException, status
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    IntegrityError,
    DataError,
    InterfaceError,
    OperationalError,
    StatementError,
    TimeoutError,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

ModelT = TypeVar("ModelT", bound=DeclarativeBase)

logger = logging.getLogger(__name__)


class DBErrorHandler:
    """
    💡 Универсальный обработчик ошибок SQLAlchemy.
    Преобразует исключения в безопасные HTTP-ответы без утечек внутренней информации.
    """

    @staticmethod
    def _is_user_data_error(err: Exception) -> bool:
        return isinstance(err, (IntegrityError, DataError, StatementError))

    @staticmethod
    def _is_connection_error(err: Exception) -> bool:
        if isinstance(
            err, (OperationalError, InterfaceError, DisconnectionError, TimeoutError)
        ):
            return True

        if isinstance(err, DBAPIError):
            return err.connection_invalidated

        return False

    @staticmethod
    def _build_detail(err: Exception, detail: str) -> str | dict[str, str]:
        if not settings.debug:
            return detail

        return {
            "message": detail,
            "error_type": err.__class__.__name__,
            "traceback": "".join(
                traceback.format_exception(type(err), err, err.__traceback__)
            ),
        }

    @staticmethod
    def handle(err: Exception, model: Type[ModelT], action: str = "processing") -> None:
        """
        Обрабатывает SQLAlchemy исключения и выбрасывает HTTPException с корректным статусом.
        """
        # Ошибки данных пользователя
        if DBErrorHandler._is_user_data_error(err):
            logger.warning(
                "Validation error in %s during %s: %s",
                model.__name__,
                action,
                err.__class__.__name__,
                exc_info=settings.debug,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=DBErrorHandler._build_detail(
                    err,
                    "Invalid data. Please check your request and try again.",
                ),
            )

        # Ошибки соединения / инфраструктуры
        if DBErrorHandler._is_connection_error(err):
            logger.error(
                "Database connection error in %s during %s: %s",
                model.__name__,
                action,
                err.__class__.__name__,
                exc_info=settings.debug,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=DBErrorHandler._build_detail(
                    err,
                    "The service is temporarily unavailable. Please try again later.",
                ),
            )

        # Неизвестные ошибки
        else:
            logger.exception(f"Unexpected DB error in {model.__name__} during {action}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=DBErrorHandler._build_detail(
                    err,
                    "Internal server error. Please try again later.",
                ),
            )
