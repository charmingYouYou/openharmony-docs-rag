import logging
import sys
import uuid
from datetime import datetime
from typing import Optional


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup logger with consistent formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def generate_trace_id() -> str:
    """Generate unique trace ID for request tracking."""
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = str(uuid.uuid4())[:8]
    return f"trace-{timestamp}-{unique_id}"


class TraceLogger:
    """Logger with trace ID support."""

    def __init__(self, logger: logging.Logger, trace_id: Optional[str] = None):
        self.logger = logger
        self.trace_id = trace_id or generate_trace_id()

    def info(self, msg: str, **kwargs):
        self.logger.info(f"[{self.trace_id}] {msg}", **kwargs)

    def warning(self, msg: str, **kwargs):
        self.logger.warning(f"[{self.trace_id}] {msg}", **kwargs)

    def error(self, msg: str, **kwargs):
        self.logger.error(f"[{self.trace_id}] {msg}", **kwargs)

    def debug(self, msg: str, **kwargs):
        self.logger.debug(f"[{self.trace_id}] {msg}", **kwargs)
