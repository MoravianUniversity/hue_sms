from phue import PhueException
from twilio.twiml.messaging_response import MessagingResponse
from flask import Flask, request, jsonify
from getRedisColor import getColor
from hue_controller import HueController
from name_converter import clean_name
from hue_color import is_excluded_palette_color, parse_rgb_values
from data_writer import writeFile, color_percent, mostRecentColors, numOfEachColor, invalidColors, first_entry_date
from display_state import advance_cycle_color, build_state, is_likely_unsupported_color_name, publish_state, publish_unsupported_color
from health_check import check_hue, check_redis
import json, random, logging, redis, time
from fuzzyColors import getFuzzyColor
from PIL import ImageColor

logging.basicConfig(level=logging.INFO,filename="hue_log.log",
                    format="%(asctime)s:%(levelname)s:%(message)s"	)

app = Flask(__name__)
controller = HueController()
file = "data.csv"
LAST_WEBHOOK_KEY = "webhook:last"


def HEX_to_RGB(hexcode_color):
    try:
        r, g, b = ImageColor.getcolor(hexcode_color, 'RGB')
        rgb_string = str(r) + ',' + str(g) + ',' + str(b)
        return rgb_string
    except ValueError:
        return None


UNSUPPORTED_COLOR_MESSAGE = (
    "That color can't be shown on the light — blacks, grays, browns, and similar "
    "muted colors don't work well. Try something brighter!"
)


def publish_color_to_display(color_name, rgb_values, subtitle=None):
    publish_state(build_state(color_name, rgb_values, mode="spotlight", subtitle=subtitle))


def get_color_names_from_redis(database):
    names = []
    for color in database.hkeys('colors'):
        if isinstance(color, bytes):
            color = color.decode('utf-8')
        if color not in ('random', 'black'):
            names.append(color)
    return names


def increment_color_usage(database, color_name):
    if database.hexists('color_totals', color_name):
        database.hincrby('color_totals', color_name, 1)
        database.incr('total', 1)


def record_incoming_webhook(database, body, from_num):
    payload = {
        "timestamp": time.time(),
        "method": request.method,
        "path": request.path,
        "from": from_num,
        "body": body,
        "remote_addr": request.remote_addr,
    }
    database.set(LAST_WEBHOOK_KEY, json.dumps(payload))
    logging.info(
        "Incoming webhook %s %s from=%s body=%r remote=%s",
        request.method,
        request.path,
        from_num,
        body,
        request.remote_addr,
    )


def get_last_webhook(database):
    raw = database.get(LAST_WEBHOOK_KEY)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


@app.route('/', methods=['POST', 'GET'])
@app.route('/sms', methods=['POST', 'GET'])
def set_color():
    is_random = False
    is_Fuzzy = False
    is_Hex = False
    database = redis.Redis(host='localhost', port=6379, db=0)

    color_names = get_color_names_from_redis(database)

    phone_number = request.values.get('From', None)
    unclean_color_name = request.values.get('Body', '') or ''
    record_incoming_webhook(database, unclean_color_name, phone_number)
    if unclean_color_name.startswith("#"):
        is_Hex = True
    color_name = clean_name(unclean_color_name)

    if not color_name:
        response = MessagingResponse()
        response.message("Please text a color name.")
        return str(response), 200, {'Content-Type': 'text/xml'}

    if color_name == "black":
        publish_unsupported_color(unclean_color_name or color_name, subtitle="Not possible on a light")
        response = MessagingResponse()
        response.message("Haha... please use a color that contains light.")
        return str(response), 200, {'Content-Type': 'text/xml'}

    if color_name == "options":
        response = MessagingResponse()
        response.message("\n***Options***\n-------------------------------\n"
                         + "'Options' - list all options for Philips Light functions\n"
                         "'Colors List' - link to list of color choices\n"
                         "'Random' - chooses a random color for the light\n"
                         "'Next' - cycle to the next color in the rotation")
        return str(response), 200, {'Content-Type': 'text/xml'}
    if color_name == "colors list":
        response = MessagingResponse()
        response.message(
            "List of color choices:" + "https://en.wikipedia.org/wiki/List_of_Crayola_crayon_colors"
        )
        return str(response), 200, {'Content-Type': 'text/xml'}

    try:
        controller.connect()
    except PhueException:
        logging.info("Server unable to connect to the Hue Light")
        response = MessagingResponse()
        response.message("Server unable to connect to the Hue Light")
        return str(response), 200, {'Content-Type': 'text/xml'}

    if color_name in ("next", "cycle"):
        try:
            color_name = advance_cycle_color()
        except ValueError:
            logging.info("No colors available for next/cycle command")
            response = MessagingResponse()
            response.message("Color list is unavailable. Run sync_colors.py first.")
            return str(response), 200, {'Content-Type': 'text/xml'}
        increment_color_usage(database, color_name)
    elif color_name == "random":
        is_random = True
        pickable = [name for name in color_names if name != 'random']
        if not pickable:
            response = MessagingResponse()
            response.message("No colors available for random.")
            return str(response), 200, {'Content-Type': 'text/xml'}
        color_name = random.choice(pickable)
        increment_color_usage(database, 'random')
    else:
        if color_name not in color_names:
            fuzzy_Color = getFuzzyColor(color_name)
            if fuzzy_Color is not None:
                is_Fuzzy = True
                color_name = clean_name(fuzzy_Color)

        if color_name in color_names:
            increment_color_usage(database, color_name)

    if is_Hex:
        rgb_values = HEX_to_RGB(unclean_color_name)

    else:
        rgb_values = getColor(color_name)

    if rgb_values is None:
        logging.info("Color " + color_name + " was not recognized")
        if is_likely_unsupported_color_name(color_name):
            publish_unsupported_color(color_name, subtitle="Not possible on a light")
            response = MessagingResponse()
            response.message(UNSUPPORTED_COLOR_MESSAGE)
            return str(response), 200, {'Content-Type': 'text/xml'}
        response = MessagingResponse()
        response.message("I'm sorry, but I don't recognize the color \"{}\".".format(color_name))
        return str(response), 200, {'Content-Type': 'text/xml'}

    r, g, b = parse_rgb_values(rgb_values)
    if is_excluded_palette_color(r, g, b):
        publish_unsupported_color(unclean_color_name or color_name, subtitle="Not possible on a light")
        response = MessagingResponse()
        response.message(UNSUPPORTED_COLOR_MESSAGE)
        return str(response), 200, {'Content-Type': 'text/xml'}

    display_color_name = clean_name(color_name)
    if is_Hex:
        display_color_name = unclean_color_name

    try:
        controller.set_rgb(rgb_values)
        logging.info("The light was changed to the color " + color_name)
        if is_random:
            message = "The light was changed to the color \"{}\". Random was used." \
                .format(clean_name(color_name))
            subtitle = "Random pick!"
        elif unclean_color_name and clean_name(unclean_color_name) in ("next", "cycle"):
            message = "The light was changed to the color \"{}\". Text 'Next' to keep cycling." \
                .format(clean_name(color_name))
            subtitle = "Next in rotation"
        elif is_Fuzzy:
            message = "We found a color similar to what you requested... The light was changed to the color \"{}\"".format(
                clean_name(color_name))
            subtitle = "Close match!"
        elif is_Hex:
            message = "You requested a Hex Color... The light was changed to the Hex \"{}\"".format(
                unclean_color_name)
            subtitle = "Custom hex color"
        else:
            message = "The light was changed to the color \"{}\"." \
                .format(clean_name(color_name))
            subtitle = "Chosen just now!"
        publish_color_to_display(display_color_name, rgb_values, subtitle=subtitle)
    except PhueException:
        logging.info("Server unable to connect to the Hue Light")
        response = MessagingResponse()
        response.message("I'm sorry, but I cannot connect to the Hue Light. Please try again later.")
        return str(response), 200, {'Content-Type': 'text/xml'}
    except Exception:
        logging.exception("Unexpected error while changing light color")
        response = MessagingResponse()
        response.message("Something went wrong changing the light. Please try again.")
        return str(response), 200, {'Content-Type': 'text/xml'}

    if is_random:
        color_name = 'random'
    writeFile(file, str(phone_number), str(color_name if not is_Hex else display_color_name), str(message))
    if is_Hex:
        response = MessagingResponse()
        response.message(message)
        return str(response), 200, {'Content-Type': 'text/xml'}

    percent = color_percent(color_name)
    date = first_entry_date(file)
    response = MessagingResponse()
    response.message(
        message + " This entry has been chosen {:.1f}".format(percent) + "% of the time since " + date + "!")
    logging.info("Color " + color_name + " has been set by the phone number " + phone_number + ".")

    return str(response), 200, {'Content-Type': 'text/xml'}


@app.route('/health', methods=['GET'])
def health():
    database = redis.Redis(host='localhost', port=6379, db=0)
    status = {
        "redis": check_redis(),
        "hue": check_hue(controller),
        "last_webhook": get_last_webhook(database),
    }
    status["ok"] = status["redis"] and status["hue"]
    code = 200 if status["ok"] else 503
    return jsonify(status), code


@app.route('/recents', methods=['GET'])
def get_most_recent():
    return mostRecentColors(file)


@app.route('/number', methods=['GET'])
def get_num_of_each():
    return numOfEachColor(file)


@app.route('/invalids', methods=['GET'])
def get_invalids():
    return invalidColors(file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    logging.info("Server has been stopped")
