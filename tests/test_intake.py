from novel_forge.intake import expansion_scope, parse_chapter_samples


def test_parse_multiple_chapter_samples():
    text = "Chapter 1: Arrival\nThe train stopped.\n\n## Chapter 2 — Bargain\nShe made the choice."
    samples = parse_chapter_samples(text)
    assert [(s.number, s.title) for s in samples] == [(1, "Arrival"), (2, "Bargain")]
    assert samples[0].content == "The train stopped."


def test_expansion_scope_requires_preservation():
    scope = expansion_scope("A short author passage.", 2500)
    assert "Preserve" in scope
    assert "2500" in scope
    assert "do not silently discard" in scope
