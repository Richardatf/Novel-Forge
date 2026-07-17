import pytest
from pydantic import ValidationError

from novel_forge.models import ChapterDraft, StoryBibleDraft


def test_structured_output_validation():
    valid = ChapterDraft(title="One", content="Specific prose. " * 20, summary="Opening", continuity_facts=[])
    assert valid.title == "One"
    with pytest.raises(ValidationError):
        ChapterDraft(title="", content="short", summary="")
    with pytest.raises(ValidationError):
        StoryBibleDraft(entries=[], voice_charter="")

