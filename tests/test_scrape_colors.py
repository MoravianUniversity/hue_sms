
from generate_colors.scrape_colors import make_map


def assert_color_equals(colors, color_input, expected_r, expected_g, expected_b):
    color = colors.get(color_input)
    assert color is not None
    assert (color["r"], color["g"], color["b"]) == (expected_r, expected_g, expected_b)


def test_color_load():
    colors = make_map("src/generate_colors/wikipedia_pages/colors.html")

    assert_color_equals(colors, "Red", 237, 10, 63)
    assert_color_equals(colors, "Lemon Yellow", 255, 255, 159)
    assert_color_equals(colors, "Violet (II)", 131, 89, 163)
    assert_color_equals(colors, "White", 255, 255, 255)
    assert_color_equals(colors, "Radical Red", 255, 53, 94)
    assert_color_equals(colors, "Fiery Rose", 255, 84, 112)
    assert_color_equals(colors, "Alloy Orange", 196, 98, 16)


def test_extracts_specialty_colors():
    colors = make_map("src/generate_colors/wikipedia_pages/colors.html")
    assert "Absolute Zero" in colors
    assert "Aztec Gold" in colors
    assert len(colors) > 300
