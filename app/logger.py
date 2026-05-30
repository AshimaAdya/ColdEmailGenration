import json
import logging
import logging.handlers
import time
from pathlib import Path


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("step", "duration_ms", "url", "job_count"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(_JsonFormatter())
    logger.addHandler(console)

    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "cold_email.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_JsonFormatter())
    logger.addHandler(file_handler)

    return logger


class Timer:
    """Context manager that logs step duration."""
    def __init__(self, logger: logging.Logger, step: str, **extra):
        self._logger = logger
        self._step = step
        self._extra = extra
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self._start) * 1000
        if exc_type:
            self._logger.error(
                "Step '%s' failed",
                self._step,
                exc_info=True,
                extra={"step": self._step, "duration_ms": round(duration_ms, 1), **self._extra},
            )
        else:
            self._logger.info(
                "Step '%s' completed",
                self._step,
                extra={"step": self._step, "duration_ms": round(duration_ms, 1), **self._extra},
            )
        return False  # don't suppress exceptions
