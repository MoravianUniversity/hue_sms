import json
import urllib.error
import urllib.request

import redis
from phue import PhueException

from config import get_redis


def check_redis(host=None, port=None):
    try:
        if host is None and port is None:
            get_redis().ping()
        else:
            redis.Redis(
                host=host or "localhost",
                port=port or 6379,
                db=0,
            ).ping()
        return True
    except redis.RedisError:
        return False


def check_hue(controller):
    try:
        controller.connect()
        return controller.light is not None
    except PhueException:
        return False


def fetch_hue_flask_health(url="http://127.0.0.1:5000/health", timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
