import os
import re
import sys

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from bs4 import BeautifulSoup

from name_converter import clean_name

from hue_color import is_excluded_palette_color

HEX_PATTERN = re.compile(r"#([0-9A-Fa-f]{6})")
RGB_PATTERN = re.compile(r"\((\d+),\s*(\d+),\s*(\d+)\)")
WIKIPEDIA_PAGE = os.path.join(os.path.dirname(__file__), "wikipedia_pages", "colors.html")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "colors.csv")


def _extract_color_name(text):
    text = text.strip()
    if not text:
        return None
    if "(" in text:
        suffix = text.split("(", 1)[1].rstrip(")").strip().lower()
        if suffix not in ("i", "ii", "iii", "iv"):
            text = text.split("(", 1)[0].strip()
    return text or None


def _parse_hex(text):
    match = HEX_PATTERN.search(text)
    if not match:
        return None
    value = match.group(1)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _parse_rgb_fields(fields):
    for field in fields:
        match = RGB_PATTERN.search(field.get_text())
        if match:
            return tuple(int(match.group(i)) for i in range(1, 4))
    return None


def _is_wikitable(table):
    classes = table.get("class") or []
    return "wikitable" in classes and "navbox" not in classes


def _is_hsv_table(table):
    matches = 0
    for row in table.find_all("tr"):
        fields = row.find_all("td")
        if len(fields) < 7:
            continue
        try:
            int(fields[4].get_text().strip())
            int(fields[5].get_text().strip())
            int(fields[6].get_text().strip())
            matches += 1
        except ValueError:
            continue
    return matches >= 3


def _parse_hsv_rows(table):
    colors = []
    for row in table.find_all("tr"):
        fields = row.find_all("td")
        if len(fields) < 7:
            continue
        try:
            rgb = tuple(int(fields[i].get_text().strip()) for i in range(4, 7))
        except ValueError:
            continue
        name = _extract_color_name(fields[0].get_text())
        if name:
            colors.append((name, rgb))
    return colors


def _parse_hex_rgb_rows(table):
    colors = []
    for row in table.find_all("tr"):
        fields = row.find_all("td")
        if len(fields) < 3:
            continue

        rgb = _parse_rgb_fields(fields)
        if rgb is None:
            continue

        first = _extract_color_name(fields[0].get_text())
        second = _extract_color_name(fields[1].get_text()) if len(fields) > 1 else None
        if first and first.isdigit() and second:
            name = second
        else:
            name = first

        if not name or name.isdigit():
            continue

        colors.append((name, rgb))
    return colors


def _row_has_hex_cells(row):
    cells = row.find_all("td")
    if not cells:
        return False
    hex_cells = sum(1 for cell in cells if _parse_hex(cell.get_text()))
    return hex_cells >= max(1, len(cells) // 2)


def _parse_name_hex_grid(table):
    colors = []
    rows = table.find_all("tr")
    index = 0
    while index < len(rows):
        row = rows[index]
        if _row_has_hex_cells(row):
            index += 1
            continue

        name_cells = row.find_all("td")
        names = [_extract_color_name(cell.get_text()) for cell in name_cells]
        if index + 1 >= len(rows) or not _row_has_hex_cells(rows[index + 1]):
            index += 1
            continue

        hex_row = rows[index + 1]
        hex_cells = hex_row.find_all("td")
        for name, cell in zip(names, hex_cells):
            rgb = _parse_hex(cell.get_text())
            if name and rgb:
                colors.append((name, rgb))
        index += 2
    return colors


def _parse_color_mix_up(table):
    colors = []
    rows = table.find_all("tr")
    index = 0
    while index < len(rows):
        row = rows[index]
        group_cells = row.find_all("td", attrs={"colspan": True})
        if not group_cells:
            index += 1
            continue
        if index + 1 >= len(rows):
            break

        hex_cells = rows[index + 1].find_all("td")
        cell_index = 0
        for group_cell in group_cells:
            name = _extract_color_name(group_cell.get_text())
            colspan = int(group_cell.get("colspan", 1))
            group_hexes = hex_cells[cell_index:cell_index + colspan]
            cell_index += colspan
            if not name or not group_hexes:
                continue
            rgb = _parse_hex(group_hexes[0].get_text())
            if rgb:
                colors.append((name, rgb))
        index += 2
    return colors


def _parse_changeables(table):
    colors = []
    rows = table.find_all("tr")
    index = 0
    while index < len(rows):
        row = rows[index]
        if _row_has_hex_cells(row):
            index += 1
            continue

        name_cells = row.find_all("td")
        names = [_extract_color_name(cell.get_text()) for cell in name_cells]
        if index + 1 >= len(rows) or not _row_has_hex_cells(rows[index + 1]):
            index += 1
            continue

        hex_cells = rows[index + 1].find_all("td")
        for name, cell in zip(names, hex_cells):
            rgb = _parse_hex(cell.get_text())
            if name and rgb:
                colors.append((name, rgb))
        index += 2
    return colors


def _detect_parser(table):
    header_text = table.get_text(" ", strip=True).lower()
    if _is_hsv_table(table):
        return _parse_hsv_rows
    if "crayon name" in header_text and "prime" in header_text:
        return _parse_color_mix_up
    if "from" in header_text and "to" in header_text and "color" in header_text:
        return _parse_changeables

    for row in table.find_all("tr"):
        fields = row.find_all("td")
        if len(fields) >= 3 and _parse_rgb_fields(fields):
            return _parse_hex_rgb_rows

    return _parse_name_hex_grid


def extract_colors(file_path=WIKIPEDIA_PAGE):
    with open(file_path) as handle:
        soup = BeautifulSoup(handle.read(), "html.parser")

    ordered = []
    seen = set()
    for table in soup.find_all("table"):
        if not _is_wikitable(table):
            continue

        parser = _detect_parser(table)
        for name, rgb in parser(table):
            key = clean_name(name)
            if key in seen or key == "black":
                continue
            if is_excluded_palette_color(*rgb):
                continue
            seen.add(key)
            ordered.append((name.strip(), rgb))

    return ordered


def make_map(file_path=WIKIPEDIA_PAGE):
    color_map = {}
    for name, rgb in extract_colors(file_path):
        color_map[name] = {"r": rgb[0], "g": rgb[1], "b": rgb[2]}
    return color_map


def make_file(output_path=OUTPUT_CSV):
    colors = extract_colors()
    with open(output_path, "w") as out:
        for name, (red, green, blue) in colors:
            out.write("{},{},{},{}\n".format(name, red, green, blue))
    return len(colors)


if __name__ == "__main__":
    count = make_file()
    print("Wrote {} colors to {}".format(count, OUTPUT_CSV))
