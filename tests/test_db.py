from novel_forge.db import LockedChapterError


def test_project_and_all_required_tables_exist(db):
    pid = db.create_project("Test", "A seed")
    assert db.project(pid)["name"] == "Test"
    required = {"projects", "project_settings", "story_bible_entries", "characters", "locations", "timeline_events", "chapters", "chapter_versions", "scenes", "continuity_facts", "editorial_findings", "style_rules", "author_decisions", "exports", "book_metadata"}
    with db.connect() as con:
        actual = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert required <= actual


def test_book_metadata_round_trip(db):
    pid = db.create_project("Workspace", "Seed")
    db.update_metadata(pid, {"book_title": "The Title", "author_name": "A. Writer", "dedication": "For the readers", "front_matter_preferences": "Preface", "back_matter_preferences": "Epilogue"})
    meta = db.metadata_for(pid)
    assert meta["book_title"] == "The Title"
    assert meta["author_name"] == "A. Writer"
    assert meta["dedication"] == "For the readers"


def test_versions_are_append_only_and_locked_content_is_protected(db):
    pid = db.create_project("Test")
    cid = db.ensure_chapter(pid, 1, "Opening", "A door opens")
    v1 = db.add_chapter_version(cid, "Opening", "A" * 120)
    v2 = db.add_chapter_version(cid, "Opening revised", "B" * 120)
    assert [v["version_number"] for v in db.versions(cid)] == [2, 1]
    db.approve_version(cid, v2, lock=True)
    try:
        db.add_chapter_version(cid, "No", "C" * 120)
        assert False, "locked chapter accepted a revision"
    except LockedChapterError:
        pass
    assert len(db.versions(cid)) == 2
    try:
        db.unlock_chapter(cid, False)
        assert False, "unlock did not require confirmation"
    except LockedChapterError:
        pass
    db.unlock_chapter(cid, True)
    db.add_chapter_version(cid, "Third", "C" * 120)
    assert len(db.versions(cid)) == 3
