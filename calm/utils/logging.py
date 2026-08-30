"""
Structured logging module for CALM V2.
Supports tags like [TELEMETRY], [PREDICTION], [POLICY], [LIFECYCLE], [MEMORY], [BENCHMARK].
"""

import logging
import sys


class TaggedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        tag = getattr(record, "tag", "CALM")
        orig_msg = record.getMessage()
        record.msg = f"[{tag}] {orig_msg}"
        return super().format(record)


def get_logger(name: str = "calm", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = TaggedFormatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
