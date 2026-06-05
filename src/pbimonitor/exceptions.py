class PbimonitorError(Exception):
    pass


class SeleniumTimeout(PbimonitorError):
    pass


class SessionExpired(PbimonitorError):
    pass


class DiffComputationError(PbimonitorError):
    pass


class StorageError(PbimonitorError):
    pass
