"""Import legacy data.csv rows into Redis when the event log is empty."""

import argparse

from config import data_file_path
from event_repository import EventRepository


def go(csv_path=None):
    path = csv_path or data_file_path()
    repo = EventRepository()
    imported = repo.import_from_csv(path)
    if imported:
        print("Imported {} event(s) from {} into Redis.".format(imported, path))
    else:
        print("No events imported (missing file or Redis log already has entries).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate CSV event log into Redis.")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="Path to data.csv (default: settings event_log_path or src/data.csv)",
    )
    args = parser.parse_args()
    go(csv_path=args.csv_path)
