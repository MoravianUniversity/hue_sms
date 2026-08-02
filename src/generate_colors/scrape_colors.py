"""Legacy shim — use hue_sms.generate_colors.scrape_colors instead."""

from hue_sms.generate_colors.scrape_colors import *  # noqa: F403
from hue_sms.generate_colors.scrape_colors import OUTPUT_CSV, make_file

if __name__ == "__main__":
    count = make_file()
    print("Wrote {} colors to {}".format(count, OUTPUT_CSV))
