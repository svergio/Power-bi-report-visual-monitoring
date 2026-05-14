class PbimonitorError(Exception):
    """Базовое исключение сбоев монитора."""


class SeleniumTimeout(PbimonitorError):
    """Операция Selenium превысила заданный таймаут."""


class SessionExpired(PbimonitorError):
    """Сессия авторизации недействительна."""


class DiffComputationError(PbimonitorError):
    """Ошибка при сравнении изображений или построении дельты."""


class StorageError(PbimonitorError):
    """Ошибка операции хранилища."""
