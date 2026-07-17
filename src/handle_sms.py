"""Orchestrate one incoming SMS: resolve color, drive bulb, update display, log."""

import logging

from phue import PhueException

from color_resolver import (
    ColorResolver,
    COMMAND_BLACK,
    COMMAND_COLORS_LIST,
    COMMAND_CYCLE_UNAVAILABLE,
    COMMAND_EMPTY,
    COMMAND_OPTIONS,
    COMMAND_RANDOM_EMPTY,
    ERROR_UNSUPPORTED,
    MATCH_FUZZY,
    MATCH_HEX,
    MATCH_RANDOM,
    ResolutionError,
    ResolvedColor,
    SpecialCommand,
)
from config import data_file_path, get_redis
from data_writer import color_percent, first_entry_date, writeFile
from display_state import build_state, publish_state, publish_unsupported_color
from hue_controller import HueController
from name_converter import clean_name

UNSUPPORTED_COLOR_MESSAGE = (
    "That color can't be shown on the light — blacks, grays, browns, and similar "
    "muted colors don't work well. Try something brighter!"
)


def increment_color_usage(database, color_name):
    if database.hexists("color_totals", color_name):
        database.hincrby("color_totals", color_name, 1)
        database.incr("total", 1)


def publish_color_to_display(color_name, rgb_values, subtitle=None):
    publish_state(build_state(color_name, rgb_values, mode="spotlight", subtitle=subtitle))


def success_message(resolved):
    if resolved.match_kind == MATCH_RANDOM:
        return (
            'The light was changed to the color "{}". Random was used.'.format(
                clean_name(resolved.color_key)
            ),
            "Random pick!",
        )
    if resolved.raw_input and clean_name(resolved.raw_input) in ("next", "cycle"):
        return (
            'The light was changed to the color "{}". Text \'Next\' to keep cycling.'.format(
                clean_name(resolved.color_key)
            ),
            "Next in rotation",
        )
    if resolved.match_kind == MATCH_FUZZY:
        return (
            'We found a color similar to what you requested... The light was changed to the color "{}"'.format(
                clean_name(resolved.color_key)
            ),
            "Close match!",
        )
    if resolved.match_kind == MATCH_HEX:
        return (
            'You requested a Hex Color... The light was changed to the Hex "{}"'.format(
                resolved.display_name
            ),
            "Custom hex color",
        )
    return (
        'The light was changed to the color "{}".'.format(clean_name(resolved.color_key)),
        "Chosen just now!",
    )


def message_for_special_command(command):
    if command.command == COMMAND_EMPTY:
        return "Please text a color name."
    if command.command == COMMAND_BLACK:
        publish_unsupported_color(command.raw_input or "black", subtitle="Not possible on a light")
        return "Haha... please use a color that contains light."
    if command.command == COMMAND_OPTIONS:
        return (
            "\n***Options***\n-------------------------------\n"
            + "'Options' - list all options for Philips Light functions\n"
            + "'Colors List' - link to list of color choices\n"
            + "'Random' - chooses a random color for the light\n"
            + "'Next' - cycle to the next color in the rotation"
        )
    if command.command == COMMAND_COLORS_LIST:
        return (
            "List of color choices:"
            + "https://en.wikipedia.org/wiki/List_of_Crayola_crayon_colors"
        )
    if command.command == COMMAND_CYCLE_UNAVAILABLE:
        logging.info("No colors available for next/cycle command")
        return "Color list is unavailable. Run sync_colors.py first."
    if command.command == COMMAND_RANDOM_EMPTY:
        return "No colors available for random."
    return "Something went wrong. Please try again."


def message_for_resolution_error(error):
    logging.info("Color %s was not recognized", error.color_key)
    if error.reason == ERROR_UNSUPPORTED:
        publish_unsupported_color(error.raw_input or error.color_key, subtitle="Not possible on a light")
        return UNSUPPORTED_COLOR_MESSAGE
    return 'I\'m sorry, but I don\'t recognize the color "{}".'.format(error.color_key)


class SmsRequestHandler:
    """Run the full SMS use case without Flask or Twilio."""

    def __init__(
        self,
        controller=None,
        resolver=None,
        event_log_path=None,
        get_database_fn=None,
    ):
        self.controller = controller or HueController()
        self.resolver = resolver or ColorResolver()
        self.event_log_path = event_log_path or data_file_path()
        self._get_database = get_database_fn or get_redis

    def handle(self, body, from_number=None):
        database = self._get_database()
        result = self.resolver.resolve(body or "", database)

        if isinstance(result, SpecialCommand):
            return message_for_special_command(result)

        try:
            self.controller.connect()
        except PhueException:
            logging.info("Server unable to connect to the Hue Light")
            return "Server unable to connect to the Hue Light"

        if isinstance(result, ResolutionError):
            return message_for_resolution_error(result)

        return self._apply_color(result, from_number, database)

    def _apply_color(self, resolved, from_number, database):
        if resolved.increment_stats:
            increment_color_usage(database, resolved.stat_key)

        try:
            self.controller.set_rgb(resolved.rgb)
            logging.info("The light was changed to the color %s", resolved.color_key)
            message, subtitle = success_message(resolved)
            publish_color_to_display(resolved.display_name, resolved.rgb, subtitle=subtitle)
        except PhueException:
            logging.info("Server unable to connect to the Hue Light")
            return "I'm sorry, but I cannot connect to the Hue Light. Please try again later."
        except Exception:
            logging.exception("Unexpected error while changing light color")
            return "Something went wrong changing the light. Please try again."

        writeFile(
            self.event_log_path,
            str(from_number),
            str(resolved.stat_key),
            str(message),
        )

        if resolved.match_kind == MATCH_HEX:
            return message

        percent = color_percent(resolved.stat_key)
        date = first_entry_date(self.event_log_path)
        logging.info(
            "Color %s has been set by the phone number %s.",
            resolved.stat_key,
            from_number,
        )
        return (
            message
            + " This entry has been chosen {:.1f}".format(percent)
            + "% of the time since "
            + date
            + "!"
        )


def handle_sms_request(body, from_number=None, handler=None):
    """Convenience wrapper used by the Flask app."""
    sms_handler = handler or SmsRequestHandler()
    return sms_handler.handle(body, from_number)
