from __future__ import annotations

import os

import streamlit as st

from novel_forge.ai import GenerationService
from novel_forge.auth import login_required
from novel_forge.config import settings
from novel_forge.db import Database, LockedChapterError
from novel_forge.intake import expansion_scope, parse_chapter_samples
from novel_forge.services import build_retrieval_bundle


st.set_page_config(page_title="The Novel Forge", page_icon="📖", layout="wide")
st.markdown("""
<style>
:root { --ink:#29251f; --paper:#f7f2e8; --brass:#8b6b36; }
.stApp { background:var(--paper); color:var(--ink); }
h1,h2,h3 { font-family:Georgia,serif; letter-spacing:.01em; }
[data-testid="stSidebar"] { background:#e9e0d1; }
.stButton button { border-radius:3px; border-color:var(--brass); }
</style>
""", unsafe_allow_html=True)

login_required()

db = Database()
db.initialize()


def generation_service(project_id: int, operation: str):
    try:
        return GenerationService()
    except Exception as exc:
        db.record_error(project_id, operation, str(exc))
        st.error(str(exc))
        return None


def selected_project():
    projects = db.projects()
    if not projects:
        return None
    labels = {f"{p['name']} · #{p['id']}": p["id"] for p in projects}
    chosen = st.sidebar.selectbox("Open project", labels, key="project_picker")
    return db.project(labels[chosen])


st.sidebar.title("The Novel Forge")
if os.getenv("NOVEL_FORGE_HOSTED", "").lower() in {"1", "true", "yes"}:
    st.sidebar.warning("Hosted storage may be temporary. Download backups frequently; local mode remains the safest home for a private manuscript.")
if st.session_state.get("novel_forge_authenticated") and st.sidebar.button("Sign out"):
    st.session_state.pop("novel_forge_authenticated", None)
    st.rerun()
page = st.sidebar.radio("Studio", ["Projects", "Seed Interview", "Story Bible", "Outline", "Manuscript", "Continuity", "Editorial Desk", "KDP Studio"])
project = selected_project()

if page == "Projects":
    st.title("Projects")
    st.caption("A private, local workspace. API keys remain in your environment and are never saved here.")
    with st.form("new_project", clear_on_submit=True):
        name = st.text_input("Project name", help="Your private workspace name; it may be the same as the book title.")
        book_title = st.text_input("Book title")
        author_name = st.text_input("Author / pen name")
        dedication = st.text_area("Dedication (optional)")
        seed = st.text_area("Novel seed", placeholder="A few sentences are enough to begin.")
        if st.form_submit_button("Create project", type="primary"):
            if not name.strip():
                st.error("Give the project a name.")
            else:
                pid = db.create_project(name, seed)
                db.update_metadata(pid, {"book_title": book_title or name, "author_name": author_name, "dedication": dedication})
                st.success(f"Created project #{pid}. Continue to Seed Interview.")
                st.rerun()
    if project:
        st.subheader(project["name"])
        st.write(project["seed"] or "No seed recorded yet.")
        if st.button("Create local database backup"):
            st.success(f"Backup created: {db.backup()}")

elif not project:
    st.warning("Create a project on the Projects page first.")

elif page == "Seed Interview":
    st.title("Seed Interview")
    s = db.settings_for(project["id"])
    meta = db.metadata_for(project["id"])
    with st.form("book_details"):
        st.subheader("Book details & publication matter")
        bd1, bd2 = st.columns(2)
        book_title = bd1.text_input("Book title", meta["book_title"])
        author_name = bd2.text_input("Author / pen name", meta["author_name"])
        dedication = st.text_area("Dedication", meta["dedication"])
        front_matter_preferences = st.text_area("Front matter to include or generate", meta["front_matter_preferences"], placeholder="For example: title page, copyright page, preface, foreword, introduction, table of contents")
        back_matter_preferences = st.text_area("Back matter to include or generate", meta["back_matter_preferences"], placeholder="For example: epilogue, acknowledgments, author note, discussion questions")
        st.caption("A preface, foreword, and introduction are front matter. An epilogue and acknowledgments normally follow the story as back matter.")
        with st.expander("Paste existing front/back-matter text"):
            preface_text = st.text_area("Preface", meta["preface_text"])
            foreword_text = st.text_area("Foreword", meta["foreword_text"])
            introduction_text = st.text_area("Introduction", meta["introduction_text"])
            epilogue_text = st.text_area("Epilogue", meta["epilogue_text"])
            acknowledgments_text = st.text_area("Acknowledgments", meta["acknowledgments_text"])
        if st.form_submit_button("Save book details"):
            db.update_metadata(project["id"], locals())
            st.success("Book details and matter preferences saved.")
    with st.form("interview"):
        seed = st.text_area("Novel seed", project["seed"], height=140)
        a, b, c = st.columns(3)
        genre = a.text_input("Genre", s["genre"]); audience = b.text_input("Target audience", s["target_audience"]); pov = c.selectbox("POV", ["", "First person", "Third limited", "Third omniscient", "Multiple POV"], index=0 if not s["pov"] else (["", "First person", "Third limited", "Third omniscient", "Multiple POV"].index(s["pov"]) if s["pov"] in ["", "First person", "Third limited", "Third omniscient", "Multiple POV"] else 0))
        tense = a.selectbox("Tense", ["", "Past", "Present"]); book_len = b.number_input("Target book length", 10000, 250000, int(s["target_book_length"]), 5000); chapter_len = c.number_input("Target chapter length", 500, 10000, int(s["target_chapter_length"]), 250)
        themes = st.text_area("Themes", s["themes"]); ending = st.text_area("Ending preferences", s["ending_preferences"]); boundaries = st.text_area("Content boundaries", s["content_boundaries"])
        prose = a.select_slider("Prose density", ["spare", "balanced", "lush"], value=s["prose_density"]); dialogue = b.select_slider("Dialogue ratio", ["low", "balanced", "high"], value=s["dialogue_ratio"]); description = c.select_slider("Description level", ["light", "balanced", "immersive"], value=s["description_level"])
        pacing = a.select_slider("Pacing", ["measured", "moderate", "fast"], value=s["pacing"]); romance = b.selectbox("Romance intensity", ["none", "subtle", "moderate", "high"], index=["none", "subtle", "moderate", "high"].index(s["romance_intensity"])); violence = c.selectbox("Violence level", ["none", "mild", "moderate", "graphic"], index=["none", "mild", "moderate", "graphic"].index(s["violence_level"]))
        religion = st.text_area("Religious constraints", s["religious_constraints"]); forbidden = st.text_area("Forbidden content", s["forbidden_content"]); comps = st.text_area("Comparable style descriptions (describe qualities; do not request living-author imitation)", s["comparable_styles"]); avoid = st.text_area("Phrases or habits to avoid", s["avoid_habits"])
        if st.form_submit_button("Save interview", type="primary"):
            db.update_interview(project["id"], seed, locals())
            st.success("Interview saved locally.")

elif page == "Story Bible":
    st.title("Story Bible")
    s = db.settings_for(project["id"])
    st.info("Generation proposes editable material. Nothing becomes manuscript text or locked canon without your approval.")
    if st.button("Generate story bible from interview", type="primary"):
        svc = generation_service(project["id"], "story_bible")
        if svc:
            try:
                interview = dict(s)
                draft = svc.story_bible(project["seed"], interview)
                db.replace_bible(project["id"], [e.model_dump() for e in draft.entries], [c.model_dump() for c in draft.characters], draft.voice_charter)
                st.success("Draft story bible created. Review and edit every entry."); st.rerun()
            except Exception as exc:
                db.record_error(project["id"], "story_bible", str(exc)); st.error(f"Generation failed safely: {exc}")
    with st.form("voice"):
        voice = st.text_area("Voice Charter", s["voice_charter"], height=220)
        if st.form_submit_button("Save Voice Charter"):
            db.update_interview(project["id"], project["seed"], {"voice_charter": voice}); st.success("Voice Charter saved.")
    for entry in db.bible(project["id"]):
        with st.expander(f"{entry['category'].title()} · {entry['title']}", expanded=False):
            with st.form(f"bible-{entry['id']}"):
                title = st.text_input("Title", entry["title"]); content = st.text_area("Content", entry["content"], height=150)
                if st.form_submit_button("Save entry"):
                    db.save_bible_entry(entry["id"], title, content); st.success("Entry saved.")
    if db.characters(project["id"]):
        st.subheader("Characters")
        for ch in db.characters(project["id"]): st.markdown(f"**{ch['name']} — {ch['role']}**  \n{ch['description']}  \nGoal: {ch['goals']}  \nContradiction: {ch['contradictions']}")

elif page == "Outline":
    st.title("Act & Chapter Outline")
    st.caption("The vertical slice supports author-created chapter cards; structured AI outline generation is the next milestone.")
    with st.form("chapter_card"):
        number = st.number_input("Chapter number", 1, 999, 1); title = st.text_input("Working title"); outline = st.text_area("Purpose and beats", height=180)
        if st.form_submit_button("Save chapter card"):
            db.ensure_chapter(project["id"], int(number), title, outline); st.success("Chapter card saved.")
    for ch in db.chapters(project["id"]): st.markdown(f"**{ch['chapter_number']}. {ch['title'] or 'Untitled'}** — {ch['status']}  \n{ch['outline']}")

elif page == "Manuscript":
    st.title("Manuscript")
    with st.expander("Drop in partial chapter drafts", expanded=not bool(db.chapters(project["id"]))):
        st.write("Paste a page or two—or more—under a heading for each chapter. The text is stored as an author-supplied version before any expansion.")
        st.code("Chapter 1: The Arrival\nPaste your prose here...\n\nChapter 2: The Bargain\nPaste your prose here...", language=None)
        samples_text = st.text_area("Chapter samples", height=300, placeholder="Chapter 1: Optional title\n\nYour draft...")
        if st.button("Import chapter samples"):
            samples = parse_chapter_samples(samples_text)
            if not samples:
                st.error("No chapter samples found. Start each sample with a heading such as “Chapter 1: The Arrival”.")
            else:
                imported = 0
                for sample in samples:
                    cid = db.ensure_chapter(project["id"], sample.number, sample.title, "Expand the author-supplied opening while preserving its intent and voice.")
                    try:
                        db.add_chapter_version(cid, sample.title or f"Chapter {sample.number}", sample.content, "Author-supplied partial draft awaiting expansion.", "author_sample", "Imported verbatim; no machine rewrite performed.")
                        imported += 1
                    except LockedChapterError:
                        st.warning(f"Chapter {sample.number} is locked, so its sample was not imported.")
                st.success(f"Imported {imported} author-supplied chapter sample(s) as new versions.")
                st.rerun()
    chapters = db.chapters(project["id"])
    if not chapters: st.warning("Add a chapter card on the Outline page first.")
    else:
        labels = {f"Chapter {c['chapter_number']}: {c['title'] or 'Untitled'}": c for c in chapters}; chapter = labels[st.selectbox("Chapter", labels)]
        versions = db.versions(chapter["id"])
        st.write(f"Status: **{chapter['status']}** · {'🔒 Locked' if chapter['is_locked'] else 'Unlocked'}")
        if chapter["is_locked"]:
            confirm = st.checkbox("I understand unlocking permits new versions but does not overwrite the approved version.")
            if st.button("Unlock chapter"):
                try: db.unlock_chapter(chapter["id"], confirm); st.success("Chapter unlocked. Approved text remains preserved."); st.rerun()
                except LockedChapterError as exc: st.error(str(exc))
        else:
            scope = st.text_area("Exact rewrite scope", "Draft the full chapter from the saved outline." if not versions else "Revise the full chapter while preserving its plot events.")
            st.warning(f"Requested scope: {scope}")
            if st.button("Generate new version", type="primary"):
                svc = generation_service(project["id"], "chapter_draft")
                if svc:
                    try:
                        draft = svc.chapter(build_retrieval_bundle(db, project["id"], chapter["chapter_number"]), chapter["chapter_number"], chapter["outline"], scope)
                        db.add_chapter_version(chapter["id"], draft.title, draft.content, draft.summary, "ai", scope)
                        st.success("New version saved separately."); st.rerun()
                    except Exception as exc: db.record_error(project["id"], "chapter_draft", str(exc)); st.error(f"Generation failed safely: {exc}")
            samples = [v for v in versions if v["source"] == "author_sample"]
            if samples:
                st.subheader("Expand an author-supplied sample")
                sample_version = st.selectbox("Source sample", samples, format_func=lambda v: f"Version {v['version_number']} · {len(v['content'].split())} words", key="sample_source")
                target_words = st.number_input("Expansion target (words)", 500, 15000, int(db.settings_for(project["id"])["target_chapter_length"]), 250)
                expand_scope = st.text_area("Exact expansion scope", expansion_scope(sample_version["content"], int(target_words)), key="expand_scope")
                st.warning(f"Requested scope: {expand_scope}")
                if st.button("Expand sample into a new version"):
                    svc = generation_service(project["id"], "chapter_expansion")
                    if svc:
                        try:
                            draft = svc.expand_chapter(build_retrieval_bundle(db, project["id"], chapter["chapter_number"]), chapter["chapter_number"], chapter["outline"], sample_version["content"], expand_scope)
                            db.add_chapter_version(chapter["id"], draft.title, draft.content, draft.summary, "ai_expansion", expand_scope)
                            st.success("Expanded chapter saved as a separate version; the source sample is unchanged."); st.rerun()
                        except Exception as exc:
                            db.record_error(project["id"], "chapter_expansion", str(exc)); st.error(f"Expansion failed safely: {exc}")
            with st.form("manual_version"):
                mt = st.text_input("Version title", chapter["title"]); mc = st.text_area("Editable chapter text", versions[0]["content"] if versions else "", height=420); ms = st.text_area("Chapter summary", versions[0]["summary"] if versions else "")
                if st.form_submit_button("Save as new version"):
                    db.add_chapter_version(chapter["id"], mt, mc, ms, "author", scope); st.success("Saved as a new version."); st.rerun()
        if versions:
            st.subheader("Version history")
            chosen = st.selectbox("Compare or approve", versions, format_func=lambda v: f"Version {v['version_number']} · {v['source']} · {v['created_at']}")
            st.text_area("Selected version", chosen["content"], height=360, disabled=True)
            lock_on_approve = st.checkbox("Lock chapter after approval", value=True)
            if st.button("Approve selected version"):
                db.approve_version(chapter["id"], chosen["id"], lock_on_approve); st.success("Version approved" + (" and locked." if lock_on_approve else ".")); st.rerun()

elif page == "Continuity":
    st.title("Continuity")
    st.write("Unresolved facts included in future chapter retrieval bundles:")
    facts = db.unresolved_facts(project["id"])
    if facts:
        for f in facts: st.write("•", f["fact"])
    else: st.info("No unresolved continuity facts recorded.")

elif page == "Editorial Desk":
    st.title("Editorial Desk")
    st.info("Separate developmental, continuity, humanization, line-editing, copyediting, and proofreading passes are planned after the vertical slice. Each will create findings or new versions, never overwrite approved text.")

elif page == "KDP Studio":
    st.title("KDP Studio")
    st.warning("KDP specifications change. Recheck Amazon KDP's current trim, margin, font, image, and file requirements before publication.")
    st.info("Print DOCX/PDF, reflowable ebook DOCX/EPUB, navigation TOC, and production preflight are the next implementation milestone after the drafting vertical slice.")
