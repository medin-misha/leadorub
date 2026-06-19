from datetime import datetime, timezone


def ensure_utc(when: datetime) -> datetime:
    """Валидирует, что дата timezone-aware, и приводит её к UTC через astimezone.

    Все запланированные таски обязаны иметь время строго в UTC, поэтому это
    единственная точка приведения во всём модуле. Наивная (без tzinfo) дата
    отклоняется намеренно: без зоны нельзя однозначно понять, локальное это
    время или уже UTC, и неявная трактовка приводит к плавающим багам.
    """
    if when.tzinfo is None:
        raise ValueError("scheduling requires a timezone-aware datetime")
    return when.astimezone(timezone.utc)
