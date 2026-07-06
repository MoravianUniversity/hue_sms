"""Rewrite palette CSV values so kiosk colors match the Hue bulb."""

import argparse
import os
import shutil

from dynaconf import Dynaconf

from hue_color import adjust_rgb_for_hue, get_gamut, is_excluded_palette_color

COLORS_DIR = os.path.dirname(os.path.abspath(__file__))


def adjust_file(path, gamut, dry_run=False):
    backup = path + ".bak"
    adjusted = []
    changed = 0
    skipped = []

    with open(path) as handle:
        lines = handle.readlines()

    for line in lines:
        raw = line.strip()
        if not raw:
            adjusted.append(line)
            continue

        name, red, green, blue = raw.split(",")
        r, g, b = int(red), int(green), int(blue)
        if is_excluded_palette_color(r, g, b):
            skipped.append(name)
            changed += 1
            continue
        mapped = adjust_rgb_for_hue(r, g, b, gamut=gamut)
        if mapped is None:
            skipped.append(name)
            continue

        nr, ng, nb = mapped
        if (nr, ng, nb) != (r, g, b):
            changed += 1
            adjusted.append("{},{},{},{}\n".format(name, nr, ng, nb))
        else:
            adjusted.append(line)

    if not dry_run:
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        with open(path, "w") as handle:
            handle.writelines(adjusted)

    return changed, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Adjust colors.csv values to match what the Hue bulb can reproduce."
    )
    parser.add_argument(
        "--gamut",
        choices=["A", "B", "C"],
        help="Hue bulb gamut (default: settings.toml hue_gamut or C)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print how many values would change without writing files",
    )
    args = parser.parse_args()

    settings = Dynaconf(settings_files=["settings.toml"])
    gamut_name = args.gamut or getattr(settings, "hue_gamut", "C")
    gamut = get_gamut(gamut_name)

    total_changed = 0
    for filename in ("colors.csv", "extra_colors.csv"):
        path = os.path.join(COLORS_DIR, filename)
        if not os.path.exists(path):
            continue
        changed, skipped = adjust_file(path, gamut, dry_run=args.dry_run)
        total_changed += changed
        if skipped:
            print("Removed {} excluded color(s) from {} (black/gray/brown/unsupported)".format(
                len(skipped), filename
            ))
        action = "Would adjust" if args.dry_run else "Adjusted"
        print("{} {} using gamut {} ({} value(s) changed)".format(
            action, filename, gamut_name, changed
        ))

    print("{} color value(s) {}.".format(
        total_changed, "would change" if args.dry_run else "changed"
    ))
    if not args.dry_run and total_changed:
        print("Run createRedis.py or sync_colors.py to push updates into Redis.")


if __name__ == "__main__":
    main()
