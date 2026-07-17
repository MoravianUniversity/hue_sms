import pytest
from phue import PhueException

from color_resolver import (
    COMMAND_EMPTY,
    MATCH_EXACT,
    MATCH_HEX,
    ResolutionError,
    ResolvedColor,
    SpecialCommand,
)
from handle_sms import SmsRequestHandler, message_for_special_command


class FakeController:
    def __init__(self, connect_raises=False, set_raises=False):
        self.connect_raises = connect_raises
        self.set_raises = set_raises
        self.connect_calls = 0
        self.last_rgb = None

    def connect(self):
        self.connect_calls += 1
        if self.connect_raises:
            raise PhueException(0, "offline")

    def set_rgb(self, rgb_values):
        if self.set_raises:
            raise PhueException(0, "offline")
        self.last_rgb = rgb_values


class FakeDatabase:
    def __init__(self):
        self.counts = {}
        self.total = 0

    def hexists(self, name, key):
        return name == "color_totals"

    def hincrby(self, name, key, amount):
        self.counts[key] = self.counts.get(key, 0) + amount

    def incr(self, key, amount=1):
        self.total += amount


@pytest.fixture
def resolved_sky_blue():
    return ResolvedColor(
        color_key="sky blue",
        display_name="sky blue",
        rgb="118,215,234",
        match_kind=MATCH_EXACT,
        raw_input="sky blue",
        stat_key="sky blue",
        increment_stats=True,
    )


def test_special_command_does_not_touch_controller():
    controller = FakeController()
    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(SpecialCommand(COMMAND_EMPTY, "")),
        get_database_fn=lambda: FakeDatabase(),
    )

    message = handler.handle("", "+15551234567")

    assert message == "Please text a color name."
    assert controller.connect_calls == 0
    assert controller.last_rgb is None


def test_resolution_error_does_not_set_bulb():
    controller = FakeController()
    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(
            ResolutionError("unknown", "notacolor", "notacolor")
        ),
        get_database_fn=lambda: FakeDatabase(),
    )

    message = handler.handle("notacolor", "+15551234567")

    assert "don't recognize" in message
    assert controller.connect_calls == 1
    assert controller.last_rgb is None


def test_successful_color_sets_bulb_and_returns_stats(
    resolved_sky_blue, monkeypatch, tmp_path
):
    controller = FakeController()
    database = FakeDatabase()
    log_file = tmp_path / "data.csv"

    monkeypatch.setattr("handle_sms.color_percent", lambda _key: 12.5)
    monkeypatch.setattr("handle_sms.first_entry_date", lambda _path: "2024-01-01")
    monkeypatch.setattr("handle_sms.writeFile", lambda path, *args: None)
    monkeypatch.setattr(
        "handle_sms.publish_color_to_display", lambda *args, **kwargs: None
    )

    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(resolved_sky_blue),
        event_log_path=str(log_file),
        get_database_fn=lambda: database,
    )

    message = handler.handle("sky blue", "+15551234567")

    assert controller.last_rgb == "118,215,234"
    assert "sky blue" in message
    assert "12.5" in message
    assert database.counts["sky blue"] == 1
    assert database.total == 1


def test_hex_color_skips_stats_suffix(monkeypatch):
    controller = FakeController()
    database = FakeDatabase()
    hex_color = ResolvedColor(
        color_key="ff2a45",
        display_name="#FF2A45",
        rgb="255,42,69",
        match_kind=MATCH_HEX,
        raw_input="#FF2A45",
        stat_key="#FF2A45",
        increment_stats=False,
    )

    monkeypatch.setattr("handle_sms.writeFile", lambda *args: None)
    monkeypatch.setattr(
        "handle_sms.publish_color_to_display", lambda *args, **kwargs: None
    )

    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(hex_color),
        get_database_fn=lambda: database,
    )

    message = handler.handle("#FF2A45", "+15551234567")

    assert controller.last_rgb == "255,42,69"
    assert "Hex" in message
    assert "% of the time" not in message
    assert database.counts == {}
    assert database.total == 0


def test_hue_connect_failure(resolved_sky_blue):
    controller = FakeController(connect_raises=True)
    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(resolved_sky_blue),
        get_database_fn=lambda: FakeDatabase(),
    )

    message = handler.handle("sky blue", "+15551234567")

    assert message == "Server unable to connect to the Hue Light"
    assert controller.last_rgb is None


def test_hue_set_failure(resolved_sky_blue, monkeypatch):
    monkeypatch.setattr(
        "handle_sms.publish_color_to_display", lambda *args, **kwargs: None
    )

    controller = FakeController(set_raises=True)
    database = FakeDatabase()
    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(resolved_sky_blue),
        get_database_fn=lambda: database,
    )

    message = handler.handle("sky blue", "+15551234567")

    assert "cannot connect to the Hue Light" in message
    assert controller.last_rgb is None
    assert database.counts["sky blue"] == 1


def test_message_for_empty_command():
    assert message_for_special_command(SpecialCommand(COMMAND_EMPTY, "")) == (
        "Please text a color name."
    )


def _resolver_returning(result):
    class StubResolver:
        def resolve(self, body, database):
            return result

    return StubResolver()
