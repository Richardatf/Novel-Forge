from __future__ import annotations

import os
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .config import settings
from .models import ChapterDraft, StoryBibleDraft

T = TypeVar("T", bound=BaseModel)


class GenerationService:
    def __init__(self, client: OpenAI | None = None, model: str | None = None):
        if client is None and not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY in your environment before using generation features.")
        self.client = client or OpenAI()
        self.model = model or settings.model

    def _structured(self, schema: type[T], instructions: str, prompt: str, retries: int = 2) -> T:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self.client.responses.parse(
                    model=self.model,
                    instructions=instructions,
                    input=prompt if attempt == 0 else f"{prompt}\nReturn valid output matching the schema exactly.",
                    text_format=schema,
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise ValueError("The model returned no structured result.")
                return parsed
            except (ValidationError, ValueError) as exc:
                last_error = exc
        raise RuntimeError(f"Structured generation failed after safe retries: {last_error}")

    def story_bible(self, seed: str, interview: dict) -> StoryBibleDraft:
        return self._structured(
            StoryBibleDraft,
            "You are a careful fiction architect. Propose editable material; never override author constraints.",
            f"NOVEL SEED:\n{seed}\n\nAUTHOR INTERVIEW:\n{interview}\n\nCreate a concise story bible and practical Voice Charter.",
        )

    def chapter(self, retrieval_bundle: str, chapter_number: int, outline: str, rewrite_scope: str) -> ChapterDraft:
        return self._structured(
            ChapterDraft,
            "Draft compelling fiction under author control. Honor every constraint. Avoid generic conclusions, repeated metaphors, excessive em dashes, uniform paragraph lengths, unnecessary restatement, and constant fragments. Build specificity, emotional causality, subtext, contradiction, individual dialogue, sensory grounding, and earned transitions.",
            f"RETRIEVAL BUNDLE:\n{retrieval_bundle}\n\nCHAPTER {chapter_number} OUTLINE:\n{outline}\n\nEXACT REWRITE SCOPE:\n{rewrite_scope or 'Draft the full chapter from its outline.'}",
        )

    def expand_chapter(self, retrieval_bundle: str, chapter_number: int, outline: str, author_sample: str, rewrite_scope: str) -> ChapterDraft:
        return self._structured(
            ChapterDraft,
            "You are a collaborative fiction writer extending author-supplied prose. The supplied text is authoritative. Preserve its voice, events, facts, and usable wording. Add specificity, emotional causality, subtext, individual dialogue, sensory grounding, varied rhythm, and earned transitions. Do not imitate a named living author.",
            f"RETRIEVAL BUNDLE:\n{retrieval_bundle}\n\nCHAPTER {chapter_number} OUTLINE:\n{outline}\n\nAUTHOR-SUPPLIED CHAPTER SAMPLE (PRESERVE):\n{author_sample}\n\nEXACT EXPANSION SCOPE:\n{rewrite_scope}",
        )
