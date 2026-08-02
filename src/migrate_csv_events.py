"""Legacy entry point — prefer: python -m hue_sms.cli.migrate_csv_events"""

from hue_sms.cli.migrate_csv_events import go

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate CSV event log into Redis.")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="Path to data.csv (default: settings event_log_path or src/data.csv)",
    )
    args = parser.parse_args()
    go(csv_path=args.csv_path)
