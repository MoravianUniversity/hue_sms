import pytest
from phue import PhueException

from hue_sms.services.color_resolver import (
    COMMAND_EMPTY,
    MATCH_EXACT,
    MATCH_HEX,
    ResolutionError,
    ResolvedColor,
    SpecialCommand,
)
from hue_sms.services.handle_sms import SmsRequestHandler, message_for_special_command


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


class FakeStats:
    def __init__(self):
        self.counts = {}
        self.total = 0

    def increment(self, color_name):
        self.counts[color_name] = self.counts.get(color_name, 0) + 1
        self.total += 1

    def percent(self, color_name):
        if self.total == 0:
            return 0.0
        return (self.counts.get(color_name, 0) / self.total) * 100


class FakeEvents:
    def __init__(self):
        self.entries = []

    def append(self, from_number, color_key, message):
        self.entries.append((from_number, color_key, message))

    def first_event_date(self):
        return "2024-01-01"


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
        stats_repo=FakeStats(),
        events_repo=FakeEvents(),
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
        stats_repo=FakeStats(),
        events_repo=FakeEvents(),
    )

    message = handler.handle("notacolor", "+15551234567")

    assert "don't recognize" in message
    assert controller.connect_calls == 1
    assert controller.last_rgb is None


def test_successful_color_sets_bulb_and_returns_stats(
    resolved_sky_blue, monkeypatch, tmp_path
):
    controller = FakeController()
    stats = FakeStats()
    events = FakeEvents()
    log_file = tmp_path / "data.csv"

    monkeypatch.setattr("hue_sms.services.handle_sms.writeFile", lambda path, *args: None)
    monkeypatch.setattr(
        "hue_sms.services.handle_sms.publish_color_to_display", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("hue_sms.services.handle_sms.csv_event_export_enabled", lambda: False)

    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(resolved_sky_blue),
        stats_repo=stats,
        events_repo=events,
        event_log_path=str(log_file),
    )

    message = handler.handle("sky blue", "+15551234567")

    assert controller.last_rgb == "118,215,234"
    assert "sky blue" in message
    assert "100.0" in message
    assert stats.counts["sky blue"] == 1
    assert len(events.entries) == 1


def test_hex_color_skips_stats_suffix(monkeypatch):
    controller = FakeController()
    stats = FakeStats()
    events = FakeEvents()
    hex_color = ResolvedColor(
        color_key="ff2a45",
        display_name="#FF2A45",
        rgb="255,42,69",
        match_kind=MATCH_HEX,
        raw_input="#FF2A45",
        stat_key="#FF2A45",
        increment_stats=False,
    )

    monkeypatch.setattr("hue_sms.services.handle_sms.writeFile", lambda *args: None)
    monkeypatch.setattr(
        "hue_sms.services.handle_sms.publish_color_to_display", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("hue_sms.services.handle_sms.csv_event_export_enabled", lambda: False)

    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(hex_color),
        stats_repo=stats,
        events_repo=events,
    )

    message = handler.handle("#FF2A45", "+15551234567")

    assert controller.last_rgb == "255,42,69"
    assert "Hex" in message
    assert "% of the time" not in message
    assert stats.counts == {}
    assert len(events.entries) == 1


def test_hue_connect_failure(resolved_sky_blue):
    controller = FakeController(connect_raises=True)
    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(resolved_sky_blue),
        stats_repo=FakeStats(),
        events_repo=FakeEvents(),
    )

    message = handler.handle("sky blue", "+15551234567")

    assert message == "Server unable to connect to the Hue Light"
    assert controller.last_rgb is None


def test_hue_set_failure(resolved_sky_blue, monkeypatch):
    monkeypatch.setattr(
        "hue_sms.services.handle_sms.publish_color_to_display", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("hue_sms.services.handle_sms.csv_event_export_enabled", lambda: False)

    controller = FakeController(set_raises=True)
    stats = FakeStats()
    events = FakeEvents()
    handler = SmsRequestHandler(
        controller=controller,
        resolver=_resolver_returning(resolved_sky_blue),
        stats_repo=stats,
        events_repo=events,
    )

    message = handler.handle("sky blue", "+15551234567")

    assert "cannot connect to the Hue Light" in message
    assert controller.last_rgb is None
    assert stats.counts["sky blue"] == 1
    assert events.entries == []


def test_message_for_empty_command():
    assert message_for_special_command(SpecialCommand(COMMAND_EMPTY, "")) == (
        "Please text a color name."
    )


def _resolver_returning(result):
    class StubResolver:
        def resolve(self, body):
            return result

    return StubResolver()
