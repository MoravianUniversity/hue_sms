import datetime
import csv
from collections import deque
from getRedisColor import getColor
import redis

DATA_FILE = "data.csv"


def writeFile(file, number, color, response):
    with open(file, mode='a') as data:
        now = datetime.datetime.now()
        data_writer = csv.writer(data, quoting=csv.QUOTE_ALL)
        data_writer.writerow([now, number, color, response])


def _format_ago(timestamp):
    if isinstance(timestamp, str):
        timestamp = timestamp.strip('"')
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp)
        except ValueError:
            timestamp = datetime.datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")
    seconds = (datetime.datetime.now() - timestamp).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return "{}m ago".format(int(seconds // 60))
    if seconds < 86400:
        return "{}h ago".format(int(seconds // 3600))
    return "{}d ago".format(int(seconds // 86400))


def _display_color_name(color_key):
    return color_key.replace("-", " ").title()


def recent_picks(file=DATA_FILE, limit=8):
    picks = []
    try:
        with open(file, 'r') as data:
            rows = list(csv.reader(data))
    except FileNotFoundError:
        return picks

    for row in reversed(rows[-limit:]):
        if len(row) < 3:
            continue
        timestamp, _, color_key = row[0].strip('"'), row[1], row[2]
        pick = {
            "color": _display_color_name(color_key),
            "key": color_key,
            "ago": _format_ago(timestamp),
        }
        rgb = getColor(color_key)
        if rgb:
            parts = [int(v) for v in rgb.split(",")]
            pick["rgb"] = parts
        picks.append(pick)
    return picks

#Returns a list of the most recent colors the Hue Light changed to up to a total of 5 colors
def mostRecentColors(file):
    colors = []
    try:
        with open(file,'r') as data:
            lastFive = deque(csv.reader(data),5)
        for i in lastFive:
            colors.append(i[2])
        return colors
    except FileNotFoundError:
        colors = []
        return colors
#Returns a dictionary of colors paired with the number of times each color has been sent to the Hue Light
def numOfEachColor(file):
    colorsDict = {}
    try:
        with open(file,'r') as data:
            data_reader = csv.reader(data)
            for row in data_reader:
                key = row[2]
                if getColor(key) is not None:
                    if key in colorsDict:
                        colorsDict[key] += 1
                    else:
                        colorsDict[key] = 1
        return colorsDict
    except FileNotFoundError:
        return colorsDict

def invalidColors(file):
    invalidList = []
    try:
        with open(file,'r') as data:
            data_reader = csv.reader(data)
            for row in data_reader:
                if getColor(row[2]) is None:
                    invalidList.append(row[2])
        return invalidList

    except FileNotFoundError:
        return invalidList


def color_percent(color):
    r = redis.Redis(host='localhost', port=6379, db=0)
    color = color.lower()

    color_raw = r.hget('color_totals', color)
    total_raw = r.get('total')
    if color_raw is None or total_raw is None:
        return 0.0

    color_total = float(color_raw.decode('utf-8'))
    total = float(total_raw.decode('utf-8'))
    if total == 0:
        return 0.0

    percent = (color_total / total) * 100

    return percent

def first_entry_date(file):
    try:
        with open(file,'r') as data:
            data_reader = csv.reader(data)
            rowOne = next(data_reader)
            firstDate = rowOne[0]
            return str(firstDate[0:10])
    except FileNotFoundError:
        return ""

