from zipfile import ZipFile

from docx import Document

from novel_forge.exports import create_ebook_docx, create_epub, create_print_docx, preflight


CHAPTERS = [{"chapter_number": 1, "title": "Arrival", "content": "First paragraph.\n\nSecond paragraph."}, {"chapter_number": 2, "title": "Choice", "content": "The choice is made."}]


def test_docx_creation(tmp_path):
    out = create_print_docx(CHAPTERS, tmp_path / "print.docx", "Test Book")
    doc = Document(out)
    assert "Test Book" in [p.text for p in doc.paragraphs]
    assert doc.sections[0].page_width.inches == 6.0


def test_ebook_toc_generation(tmp_path):
    out = create_epub(CHAPTERS, tmp_path / "book.epub", "Test Book")
    with ZipFile(out) as archive:
        names = archive.namelist()
        nav_name = next(n for n in names if n.endswith("nav.xhtml"))
        nav = archive.read(nav_name).decode("utf-8")
        assert "Arrival" in nav and "Choice" in nav


def test_export_preflight_checks():
    bad = [{"chapter_number": 1, "title": "", "content": "TODO"}, {"chapter_number": 3, "title": "End", "content": ""}]
    findings = preflight(bad)
    assert any("Missing chapter numbers: 2" in f for f in findings)
    assert any("blank heading" in f for f in findings)
    assert any("placeholder" in f for f in findings)
    assert any("empty" in f for f in findings)

