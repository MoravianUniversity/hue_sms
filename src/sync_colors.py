"""Legacy entry point — prefer: python -m hue_sms.cli.sync_colors"""

from hue_sms.cli.sync_colors import go

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync palette CSV files into Redis.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Update RGB values for colors already in Redis.",
    )
    args = parser.parse_args()
    go(refresh=args.refresh)
