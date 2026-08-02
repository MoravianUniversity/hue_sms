
from hue_sms.domain.name_converter import NameConverter, clean_name

red = (255, 54, 78)
red_orange = (255, 112, 44)
orange = (255, 140, 108)


def test_clean_caps():
    assert 'red' == clean_name('Red')
    assert 'red' == clean_name('RED')
    assert 'red' == clean_name('red')
    assert 'red' == clean_name('ReD')


def test_clean_punctuation():
    assert 'red' == clean_name('Red.')
    assert 'red' == clean_name('RED!')
    assert 'red' == clean_name('red?')


def test_clean_whitespace():
    assert 'red' == clean_name('   Red   ')
    assert 'red' == clean_name('\t\tRed\t\t')
    assert 'red' == clean_name('\n\nRed\n\n')


def test_exact_spelling():
    converter = NameConverter()
    assert red == converter.convert('Red')
    assert red_orange == converter.convert('Red-Orange')
    assert orange == converter.convert("Orange")


def test_leading_and_trailing_space():
    converter = NameConverter()
    assert red == converter.convert('  Red  ')
    assert red_orange == converter.convert('\nRed-Orange\n')
    assert orange == converter.convert("\t\tOrange\t\t")


def test_different_cases():
    converter = NameConverter()
    assert red == converter.convert('RED')
    assert red_orange == converter.convert('red-orange')
    assert orange == converter.convert("oRaNgE")


def test_punctuation():
    converter = NameConverter()
    assert red == converter.convert('Red.')
    assert red_orange == converter.convert('Red-Orange!')
    assert orange == converter.convert("Orange?")
