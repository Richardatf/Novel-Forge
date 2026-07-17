from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .config import settings


class LockedChapterError(RuntimeError):
    pass


class Database:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or settings.db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as con:
            con.executescript(schema)

    def backup(self, destination: Path | None = None) -> Path:
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        destination = destination or settings.backup_dir
        destination.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = destination / f"novel-forge-{stamp}.db"
        shutil.copy2(self.path, target)
        return target

    def create_project(self, name: str, seed: str = "") -> int:
        with self.connect() as con:
            cur = con.execute("INSERT INTO projects(name, seed) VALUES (?, ?)", (name.strip(), seed.strip()))
            project_id = int(cur.lastrowid)
            con.execute("INSERT INTO project_settings(project_id) VALUES (?)", (project_id,))
            con.execute("INSERT INTO book_metadata(project_id,book_title) VALUES (?,?)", (project_id, name.strip()))
            return project_id

    def projects(self):
        with self.connect() as con:
            return con.execute("SELECT * FROM projects ORDER BY updated_at DESC, id DESC").fetchall()

    def project(self, project_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()

    def settings_for(self, project_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM project_settings WHERE project_id=?", (project_id,)).fetchone()

    def metadata_for(self, project_id: int):
        with self.connect() as con:
            con.execute("INSERT OR IGNORE INTO book_metadata(project_id,book_title) SELECT id,name FROM projects WHERE id=?", (project_id,))
            return con.execute("SELECT * FROM book_metadata WHERE project_id=?", (project_id,)).fetchone()

    def update_metadata(self, project_id: int, values: dict) -> None:
        allowed = {"book_title", "author_name", "dedication", "front_matter_preferences", "back_matter_preferences", "preface_text", "foreword_text", "introduction_text", "acknowledgments_text", "epilogue_text"}
        clean = {k: str(v) for k, v in values.items() if k in allowed}
        if not clean:
            return
        with self.connect() as con:
            con.execute("INSERT OR IGNORE INTO book_metadata(project_id,book_title) SELECT id,name FROM projects WHERE id=?", (project_id,))
            assignments = ", ".join(f"{k}=?" for k in clean)
            con.execute(f"UPDATE book_metadata SET {assignments},updated_at=CURRENT_TIMESTAMP WHERE project_id=?", (*clean.values(), project_id))

    def update_interview(self, project_id: int, seed: str, values: dict) -> None:
        allowed = {"genre", "target_audience", "pov", "tense", "target_book_length", "target_chapter_length",
                   "prose_density", "dialogue_ratio", "description_level", "pacing", "romance_intensity",
                   "violence_level", "religious_constraints", "forbidden_content", "comparable_styles",
                   "avoid_habits", "themes", "ending_preferences", "content_boundaries", "voice_charter"}
        clean = {k: v for k, v in values.items() if k in allowed}
        assignments = ", ".join(f"{k}=?" for k in clean)
        with self.connect() as con:
            con.execute("UPDATE projects SET seed=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (seed, project_id))
            if clean:
                con.execute(f"UPDATE project_settings SET {assignments} WHERE project_id=?", (*clean.values(), project_id))

    def replace_bible(self, project_id: int, entries: list[dict], characters: list[dict], voice_charter: str) -> None:
        with self.connect() as con:
            con.execute("DELETE FROM story_bible_entries WHERE project_id=? AND is_locked=0", (project_id,))
            con.executemany("INSERT INTO story_bible_entries(project_id,category,title,content) VALUES (?,?,?,?)",
                            [(project_id, e["category"], e["title"], e["content"]) for e in entries])
            con.execute("DELETE FROM characters WHERE project_id=?", (project_id,))
            con.executemany("INSERT INTO characters(project_id,name,role,description,goals,contradictions) VALUES (?,?,?,?,?,?)",
                            [(project_id, c["name"], c.get("role", ""), c.get("description", ""), c.get("goals", ""), c.get("contradictions", "")) for c in characters])
            con.execute("UPDATE project_settings SET voice_charter=? WHERE project_id=?", (voice_charter, project_id))

    def bible(self, project_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM story_bible_entries WHERE project_id=? ORDER BY category,id", (project_id,)).fetchall()

    def characters(self, project_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM characters WHERE project_id=? ORDER BY id", (project_id,)).fetchall()

    def save_bible_entry(self, entry_id: int, title: str, content: str) -> None:
        with self.connect() as con:
            con.execute("UPDATE story_bible_entries SET title=?,content=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND is_locked=0", (title, content, entry_id))

    def ensure_chapter(self, project_id: int, number: int, title: str = "", outline: str = "") -> int:
        with self.connect() as con:
            con.execute("INSERT OR IGNORE INTO chapters(project_id,chapter_number,title,outline) VALUES (?,?,?,?)", (project_id, number, title, outline))
            row = con.execute("SELECT id FROM chapters WHERE project_id=? AND chapter_number=?", (project_id, number)).fetchone()
            return int(row["id"])

    def chapters(self, project_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM chapters WHERE project_id=? ORDER BY chapter_number", (project_id,)).fetchall()

    def chapter(self, chapter_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()

    def add_chapter_version(self, chapter_id: int, title: str, content: str, summary: str = "", source: str = "author", rewrite_scope: str = "") -> int:
        with self.connect() as con:
            chapter = con.execute("SELECT is_locked FROM chapters WHERE id=?", (chapter_id,)).fetchone()
            if chapter is None:
                raise KeyError(chapter_id)
            if chapter["is_locked"]:
                raise LockedChapterError("Unlock the chapter with explicit confirmation before revising it.")
            next_version = con.execute("SELECT COALESCE(MAX(version_number),0)+1 n FROM chapter_versions WHERE chapter_id=?", (chapter_id,)).fetchone()["n"]
            cur = con.execute("INSERT INTO chapter_versions(chapter_id,version_number,title,content,summary,source,rewrite_scope) VALUES (?,?,?,?,?,?,?)",
                              (chapter_id, next_version, title, content, summary, source, rewrite_scope))
            con.execute("UPDATE chapters SET title=?,status='drafted' WHERE id=?", (title, chapter_id))
            return int(cur.lastrowid)

    def versions(self, chapter_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM chapter_versions WHERE chapter_id=? ORDER BY version_number DESC", (chapter_id,)).fetchall()

    def approve_version(self, chapter_id: int, version_id: int, lock: bool = False) -> None:
        with self.connect() as con:
            valid = con.execute("SELECT 1 FROM chapter_versions WHERE id=? AND chapter_id=?", (version_id, chapter_id)).fetchone()
            if not valid:
                raise ValueError("Version does not belong to this chapter")
            con.execute("UPDATE chapters SET approved_version_id=?,status='approved',is_locked=? WHERE id=?", (version_id, int(lock), chapter_id))

    def unlock_chapter(self, chapter_id: int, confirmed: bool) -> None:
        if not confirmed:
            raise LockedChapterError("Confirmation is required to unlock approved text.")
        with self.connect() as con:
            con.execute("UPDATE chapters SET is_locked=0,status='approved' WHERE id=?", (chapter_id,))

    def unresolved_facts(self, project_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM continuity_facts WHERE project_id=? AND status='unresolved'", (project_id,)).fetchall()

    def decisions(self, project_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM author_decisions WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()

    def record_error(self, project_id: int | None, operation: str, error: str) -> None:
        with self.connect() as con:
            con.execute("INSERT INTO generation_errors(project_id,operation,error) VALUES (?,?,?)", (project_id, operation, error))
