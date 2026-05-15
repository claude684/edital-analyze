"""Testes do módulo utils."""

from app.utils import (
    clean_text,
    get_file_extension,
    parse_brazilian_currency,
    parse_brazilian_date,
    slugify,
)


class TestCleanText:
    def test_remove_extra_spaces(self):
        assert clean_text("hello   world") == "hello world"

    def test_normalize_line_breaks(self):
        assert clean_text("line1\r\nline2") == "line1\nline2"

    def test_empty_input(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_collapse_blank_lines(self):
        result = clean_text("a\n\n\n\nb")
        assert result == "a\n\nb"


class TestParseBrazilianCurrency:
    def test_full_format(self):
        assert parse_brazilian_currency("R$ 1.234.567,89") == 1234567.89

    def test_no_currency_symbol(self):
        assert parse_brazilian_currency("1.500,00") == 1500.00

    def test_integer_value(self):
        assert parse_brazilian_currency("R$ 1.000") == 1000.0

    def test_invalid_returns_none(self):
        assert parse_brazilian_currency("") is None
        assert parse_brazilian_currency("abc") is None


class TestParseBrazilianDate:
    def test_slash_format(self):
        assert parse_brazilian_date("15/03/2024") == "2024-03-15"

    def test_dash_format(self):
        assert parse_brazilian_date("15-03-2024") == "2024-03-15"

    def test_extenso(self):
        assert parse_brazilian_date("15 de março de 2024") == "2024-03-15"

    def test_invalid_returns_none(self):
        assert parse_brazilian_date("not a date") is None
        assert parse_brazilian_date("") is None


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_accents(self):
        assert slugify("Edital nº 045/2024") == "edital-no-0452024"

    def test_empty(self):
        assert slugify("") == "untitled"


class TestGetFileExtension:
    def test_pdf(self):
        assert get_file_extension("document.pdf") == "pdf"

    def test_uppercase(self):
        assert get_file_extension("DOC.PDF") == "pdf"

    def test_no_extension(self):
        assert get_file_extension("noext") == ""

    def test_with_path(self):
        assert get_file_extension("/path/to/file.docx") == "docx"
