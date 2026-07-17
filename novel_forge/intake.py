from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChapterSample:
    number: int
    title: str
    content: str


HEADING = re.compile(r"(?im)^\s*#{0,3}\s*chapter\s+(\d+)(?:\s*[:—-]\s*(.*?))?\s*$")


def parse_chapter_samples(text: str) -> list[ChapterSample]:
    """Parse pasted samples headed by `Chapter N: Optional title`."""
    matches = list(HEADING.finditer(text))
    samples: list[ChapterSample] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[match.end():end].strip()
        if content:
            samples.append(ChapterSample(int(match.group(1)), (match.group(2) or "").strip(), content))
    return samples


def expansion_scope(sample: str, target_words: int) -> str:
    words = len(sample.split())
    return (
        f"Preserve the supplied author text and expand Chapter content from approximately {words} words "
        f"toward {target_words} words. Add material around and between existing passages as needed; do not silently "
        "discard, contradict, or rewrite the author's supplied prose. Return the complete integrated chapter."
    )
