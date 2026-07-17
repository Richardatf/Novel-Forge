from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BibleItem(BaseModel):
    category: Literal["premise", "theme", "world", "voice", "constraint", "other"]
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)


class CharacterItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = ""
    description: str = ""
    goals: str = ""
    contradictions: str = ""


class StoryBibleDraft(BaseModel):
    entries: list[BibleItem] = Field(min_length=1)
    characters: list[CharacterItem] = Field(default_factory=list)
    voice_charter: str = Field(min_length=1)


class ChapterDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=100)
    summary: str = Field(min_length=1)
    continuity_facts: list[str] = Field(default_factory=list)

    @field_validator("content")
    @classmethod
    def reject_placeholders(cls, value: str) -> str:
        if value.strip().lower() in {"todo", "tbd", "placeholder"}:
            raise ValueError("chapter content cannot be a placeholder")
        return value


class OutlineChapter(BaseModel):
    number: int = Field(ge=1)
    title: str
    purpose: str
    beats: list[str] = Field(default_factory=list)


class OutlineDraft(BaseModel):
    chapters: list[OutlineChapter] = Field(min_length=1)

