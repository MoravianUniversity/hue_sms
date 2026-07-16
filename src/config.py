"""Shared configuration and infrastructure helpers."""

import logging
import os

import redis
from dynaconf import Dynaconf

# Project root (parent of src/) — settings.toml lives here regardless of cwd.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.dirname(os.path.abspath(__file__))

settings = Dynaconf(
    settings_files=[os.path.join(PROJECT_ROOT, "settings.toml")],
)

DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0
DEFAULT_LOG_FILE = "hue_log.log"
DEFAULT_HUE_GAMUT = "C"
DEFAULT_SMS_PHONE = "484-895-1386"
DEFAULT_HUE_HEALTH_URL = "http://127.0.0.1:5000/health"


def get_redis(decode_responses=True):
    """Return a Redis client using settings from settings.toml."""
    return redis.Redis(
        host=getattr(settings, "redis_host", DEFAULT_REDIS_HOST),
        port=int(getattr(settings, "redis_port", DEFAULT_REDIS_PORT)),
        db=int(getattr(settings, "redis_db", DEFAULT_REDIS_DB)),
        decode_responses=decode_responses,
    )


def configure_logging():
    """Configure application logging once (safe to call from multiple entrypoints)."""
    root = logging.getLogger()
    if root.handlers:
        return
    log_file = getattr(settings, "log_file", DEFAULT_LOG_FILE)
    logging.basicConfig(
        level=logging.INFO,
        filename=log_file,
        format="%(asctime)s:%(levelname)s:%(message)s",
    )


def data_file_path():
    """Path to the CSV event log (defaults to src/data.csv)."""
    configured = getattr(settings, "event_log_path", None) or getattr(
        settings, "data_file", None
    )
    if configured:
        if os.path.isabs(configured):
            return configured
        return os.path.join(PROJECT_ROOT, configured)
    return os.path.join(SRC_DIR, "data.csv")
