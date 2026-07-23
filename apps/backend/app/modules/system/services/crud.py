from fastapi import HTTPException, status
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    select,
    Result,
    String,
    or_,
    and_,
    Boolean,
    Integer,
    DateTime,
    Date,
    Float,
    func,
)
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from datetime import datetime

from typing import TypeVar, Type, Union
import logging

from .errors import DBErrorHandler

# универсальные дженерики
ModelT = TypeVar("ModelT", bound=DeclarativeBase)
SchemaT = TypeVar("SchemaT", bound=BaseModel)
logger = logging.getLogger(__name__)


class CRUD:
    @staticmethod
    async def _get_by_filters(
        model: Type[ModelT],
        session: AsyncSession,
        filters: dict[str, object],
    ) -> ModelT | None:
        """Возвращает первую запись, удовлетворяющую набору equality-фильтров."""

        stmt = select(model).where(
            *[getattr(model, field) == value for field, value in filters.items()]
        )
        result: Result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def _get_by_id(
        model: Type[ModelT],
        session: AsyncSession,
        id: int,
    ) -> ModelT:
        """
        Возвращает одну запись по первичному ключу.

        Используется интерфейсным методом `get()` в сценарии точечного чтения,
        когда клиент запрашивает конкретную сущность по `id`.

        Raises:
            HTTPException(404): если запись не найдена.
        """
        instance = await session.get(model, id)
        if instance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model.__name__} with id={id} not found.",
            )
        return instance

    @staticmethod
    def _get_field_search(
        stmt,
        model: Type[ModelT],
        model_columns: dict[str, object],
        field: str,
        search: str,
    ):
        """
        Добавляет к запросу фильтрацию по одному конкретному полю модели.

        Для строковых колонок используется частичное совпадение с автоэкранированием
        wildcard-символов. Для остальных поддерживаемых типов применяется парсинг
        значения и точное сравнение.

        Raises:
            HTTPException(400): если поле не существует в модели или значение
            нельзя преобразовать к типу колонки.
        """
        column = model_columns.get(field)
        if column is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Field '{field}' not found in {model.__name__}",
            )

        model_field = getattr(model, field)
        if isinstance(column.type, String):
            return stmt.where(model_field.contains(search, autoescape=True))

        return stmt.where(model_field == CRUD.parse_value(column, search))

    @staticmethod
    def _get_text_search(
        stmt,
        model_columns: dict[str, object],
        search: str,
    ):
        """
        Добавляет к запросу полнотекстовый поиск по всем строковым колонкам модели.

        Поиск разбивает строку на слова и строит условие в формате:
        каждое слово должно встретиться хотя бы в одном текстовом поле
        (`AND` между словами, `OR` между колонками).

        Если у модели нет строковых колонок, запрос возвращается без изменений.
        """
        text_columns = [
            column
            for column in model_columns.values()
            if isinstance(column.type, String)
        ]
        if not text_columns:
            return stmt

        words = search.split()
        if not words:
            return stmt

        word_conditions = []
        for word in words:
            field_conditions = [
                column.contains(word, autoescape=True) for column in text_columns
            ]
            word_conditions.append(or_(*field_conditions))

        return stmt.where(and_(*word_conditions))

    @staticmethod
    async def create(
        data: SchemaT, model: Type[ModelT], session: AsyncSession
    ) -> ModelT:
        """
        💡 Универсальное создание ORM-сущности.

        Создаёт новую запись в базе данных из Pydantic-схемы.
        Все ошибки SQLAlchemy автоматически обрабатываются DBErrorHandler.

        Args:
            data: Входная Pydantic-модель с данными.
            model: ORM-модель (дочерний класс Base).
            session: Асинхронная сессия SQLAlchemy.

        Returns:
            Созданный ORM-объект после refresh().

        Raises:
            HTTPException: при любой ошибке БД или некорректных данных.
        """
        try:
            instance = model(**data.model_dump())
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="creating")
        else:
            return instance

    @staticmethod
    async def get_or_create(
        data: SchemaT,
        model: Type[ModelT],
        session: AsyncSession,
        lookup_fields: tuple[str, ...],
    ) -> tuple[ModelT, bool]:
        """
        Ищет запись по набору полей и создаёт её при отсутствии.

        При гонке на уникальном ограничении повторно читает запись по тем же lookup-полям
        и возвращает уже созданный конкурентным запросом объект.
        """
        payload = data.model_dump()
        filters = {field: payload[field] for field in lookup_fields}

        try:
            instance = await CRUD._get_by_filters(
                model=model,
                session=session,
                filters=filters,
            )
            if instance is not None:
                return instance, False

            async with session.begin_nested():
                instance = model(**payload)
                session.add(instance)
                await session.flush()
            await session.refresh(instance)
            return instance, True
        except IntegrityError as err:
            instance = await CRUD._get_by_filters(
                model=model,
                session=session,
                filters=filters,
            )
            if instance is not None:
                return instance, False
            DBErrorHandler.handle(err=err, model=model, action="creating")
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="creating")

    @staticmethod
    def _apply_search(stmt, model: Type[ModelT], search: str | None, field: str | None):
        """Применяет к запросу ту же фильтрацию search/field, что и `get()`.

        Вынесено отдельно, чтобы count/get_column не дублировали логику фильтра.
        """
        search = search.strip() if search else None
        field = field.strip() if field else None
        if not search:
            return stmt

        mapper: Mapper = inspect(model)
        model_columns = {column.name: column for column in mapper.columns}
        if field is not None:
            return CRUD._get_field_search(
                stmt=stmt,
                model=model,
                model_columns=model_columns,
                field=field,
                search=search,
            )
        return CRUD._get_text_search(
            stmt=stmt,
            model_columns=model_columns,
            search=search,
        )

    @staticmethod
    async def count(
        model: Type[ModelT],
        session: AsyncSession,
        search: str | None = None,
        field: str | None = None,
    ) -> int:
        """Считает записи модели под фильтром search/field (без пагинации)."""
        try:
            stmt = CRUD._apply_search(
                select(func.count()).select_from(model), model, search, field
            )
            result: Result = await session.execute(stmt)
            return int(result.scalar_one())
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="counting")

    @staticmethod
    async def get_column(
        model: Type[ModelT],
        session: AsyncSession,
        column,
        search: str | None = None,
        field: str | None = None,
    ) -> list:
        """Возвращает значения одной колонки для всех записей под фильтром (без пагинации)."""
        try:
            stmt = CRUD._apply_search(select(column), model, search, field)
            result: Result = await session.execute(stmt)
            return list(result.scalars().all())
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="reading")

    @staticmethod
    async def get(
        model: Type[ModelT],
        session: AsyncSession,
        id: int | None = None,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
        field: str | None = None,
    ) -> Union[ModelT, list[ModelT]]:
        """
        💡 Универсальный метод чтения данных из базы.

        Если передан `id`, возвращает одну запись по первичному ключу.
        Если `id` не указан — возвращает список всех записей модели.

        Args:
            model: ORM-модель (дочерний класс Base)
            session: асинхронная сессия SQLAlchemy
            id: идентификатор записи (опционально)
            page: страница (опционально)
            limit: лимит (опционально)
            search: поисковый запрос (опционально)
            fields: поля для поиска (опционально)

        Returns:
            Один объект модели или список всех объектов.

        Raises:
            HTTPException(404): если запись по id не найдена.
            HTTPException(400/503/500): если произошла SQL-ошибка (через DBErrorHandler).
        """
        try:
            page = max(page, 1)
            limit = max(limit, 1)
            search = search.strip() if search else None
            field = field.strip() if field else None

            if id is not None:
                return await CRUD._get_by_id(model=model, session=session, id=id)

            mapper: Mapper = inspect(model)
            model_columns = {column.name: column for column in mapper.columns}
            stmt = select(model)

            if search:
                if field is not None:
                    stmt = CRUD._get_field_search(
                        stmt=stmt,
                        model=model,
                        model_columns=model_columns,
                        field=field,
                        search=search,
                    )
                else:
                    stmt = CRUD._get_text_search(
                        stmt=stmt,
                        model_columns=model_columns,
                        search=search,
                    )

            stmt = stmt.order_by(*[column.asc() for column in mapper.primary_key])
            stmt = stmt.limit(limit).offset((page - 1) * limit)
            result: Result = await session.execute(stmt)
            return result.scalars().all()
        except HTTPException:
            raise
        except Exception as err:
            # Любая ошибка SQLAlchemy или инфраструктуры
            DBErrorHandler.handle(err=err, model=model, action="reading")

    @staticmethod
    async def patch(
        new_data: SchemaT,
        model: Type[ModelT],
        session: AsyncSession,
        id: int,
    ) -> ModelT:
        """
        💡 Универсальное обновление записи (частичное).

        Обновляет только те поля, которые переданы в Pydantic-модели `new_data`.
        Если запись с указанным id не найдена, выбрасывает 404.
        Все ошибки SQLAlchemy обрабатываются через DBErrorHandler.

        Args:
            new_data: Pydantic-модель с обновлёнными полями
            model: ORM-модель
            session: асинхронная сессия SQLAlchemy
            id: идентификатор записи

        Returns:
            Обновлённый ORM-объект

        Raises:
            HTTPException(404): если запись не найдена
            HTTPException(400/503/500): при ошибках БД
        """
        try:
            stmt = select(model).where(model.id == id)
            result: Result = await session.execute(stmt)
            instance = result.scalars().first()

            if not instance:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__name__} with id={id} not found.",
                )

            # exclude_unset → обновляем только реально переданные поля
            update_data = new_data.model_dump(exclude_unset=True)

            # Защита: не даём обновить первичный ключ
            update_data.pop("id", None)

            for field, value in update_data.items():
                setattr(instance, field, value)

            await session.flush()
            await session.refresh(instance)

            return instance
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="updating")

    @staticmethod
    async def delete(
        model: Type[ModelT],
        session: AsyncSession,
        id: int,
    ) -> str:
        """
        💡 Удаляет запись по ID.

        Args:
            model: ORM-модель (дочерний класс Base)
            session: асинхронная сессия SQLAlchemy
            id: идентификатор записи для удаления

        Returns:
            Строка `"ok"` при успешном удалении.

        Raises:
            HTTPException(404): если запись не найдена
            HTTPException(400/503/500): при ошибках БД (через DBErrorHandler)
        """
        try:
            stmt = select(model).where(model.id == id)
            result: Result = await session.execute(stmt)
            instance: ModelT | None = result.scalars().first()

            if not instance:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__name__} with id={id} not found.",
                )

            await session.delete(instance)
            await session.flush()
            return "ok"
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="deleting")

    @staticmethod
    async def bulk_create(
        data: list[SchemaT], model: Type[ModelT], session: AsyncSession
    ) -> list[ModelT]:
        try:
            instances = [model(**item.model_dump()) for item in data]
            session.add_all(instances)
            await session.flush()
            for instance in instances:
                await session.refresh(instance)
        except HTTPException:
            raise
        except Exception as err:
            DBErrorHandler.handle(err=err, model=model, action="bulk creating")
        else:
            return instances

    @staticmethod
    def parse_value(column, raw_value: str):
        column_type = column.type
        boolean_map = {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
        }
        try:
            # STRING
            if isinstance(column_type, String):
                return raw_value

            # INTEGER
            elif isinstance(column_type, Integer):
                return int(raw_value)

            # FLOAT
            elif isinstance(column_type, Float):
                return float(raw_value)

            # BOOLEAN
            elif isinstance(column_type, Boolean):
                value = raw_value.lower()
                if value not in boolean_map:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value '{raw_value}' for field '{column.name}'",
                    )

                return boolean_map[value]

            # DATE
            elif isinstance(column_type, Date):
                return datetime.strptime(raw_value, "%Y-%m-%d").date()

            # DATETIME
            elif isinstance(column_type, DateTime):
                return datetime.fromisoformat(raw_value)

            # fallback
            return raw_value

        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value '{raw_value}' for field '{column.name}'",
            )
