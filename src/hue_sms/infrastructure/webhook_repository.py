"""Redis access for the last incoming SMS webhook audit entry."""

import json

from hue_sms.config import get_redis

LAST_WEBHOOK_KEY = "webhook:last"


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


class WebhookRepository:
    def __init__(self, redis_client=None):
        self.redis = redis_client or get_redis()

    def record(self, payload):
        self.redis.set(LAST_WEBHOOK_KEY, json.dumps(payload))

    def get_last(self):
        raw = self.redis.get(LAST_WEBHOOK_KEY)
        if raw is None:
            return None
        return json.loads(_decode(raw))
