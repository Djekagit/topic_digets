import logging
import sys
from pathlib import Path

from loguru import logger


_CONFIGURED = False
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {extra[logger_name]} - {message}"


def _set_default_logger_name(record):
    record["extra"].setdefault("logger_name", record["name"])


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.bind(logger_name=record.name).opt(exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    Path("logs").mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.configure(patcher=_set_default_logger_name)
    logger.add(sys.stdout, level="INFO", format=LOG_FORMAT)
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
        level="INFO",
        format=LOG_FORMAT,
        backtrace=False,
        diagnose=False,
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiogram").propagate = True
    for logger_name in ("apscheduler", "aiohttp", "httpx", "sqlalchemy", "sqlalchemy.engine", "sqlalchemy.orm"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
        logging.getLogger(logger_name).propagate = True
    _CONFIGURED = True


__all__ = ["logger", "setup_logging"]
