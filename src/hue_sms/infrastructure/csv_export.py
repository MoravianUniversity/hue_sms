"""Optional CSV export for SMS events (see settings csv_event_export)."""

import csv
import datetime


def writeFile(file, number, color, response):
    with open(file, mode="a") as data:
        now = datetime.datetime.now()
        writer = csv.writer(data, quoting=csv.QUOTE_ALL)
        writer.writerow([now, number, color, response])
