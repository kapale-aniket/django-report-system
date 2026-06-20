import logging


def get_logger(name: str = 'reportflow') -> logging.Logger:
    return logging.getLogger(name)


def log_api_error(logger: logging.Logger, message: str, exc: Exception | None = None, **extra):
    if exc:
        logger.exception(message, exc_info=exc, extra=extra)
    else:
        logger.error(message, extra=extra)
