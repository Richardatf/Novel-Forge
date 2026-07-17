from __future__ import annotations

from .db import Database


def build_retrieval_bundle(db: Database, project_id: int, chapter_number: int) -> str:
    project = db.project(project_id)
    settings = db.settings_for(project_id)
    bible = db.bible(project_id)
    characters = db.characters(project_id)
    facts = db.unresolved_facts(project_id)
    decisions = db.decisions(project_id)
    preceding = "None (opening chapter)."
    chapters = db.chapters(project_id)
    prior = next((c for c in chapters if c["chapter_number"] == chapter_number - 1), None)
    if prior and prior["approved_version_id"]:
        preceding = next((v["summary"] for v in db.versions(prior["id"]) if v["id"] == prior["approved_version_id"]), "No summary recorded.")
    return "\n\n".join([
        f"Seed: {project['seed']}",
        f"Voice Charter: {settings['voice_charter'] or 'Not yet defined.'}",
        "Writing controls: " + "; ".join(f"{k}={settings[k]}" for k in ("genre", "target_audience", "pov", "tense", "prose_density", "dialogue_ratio", "description_level", "pacing", "romance_intensity", "violence_level", "religious_constraints", "forbidden_content", "comparable_styles", "avoid_habits")),
        "Relevant bible: " + " | ".join(f"{b['title']}: {b['content']}" for b in bible),
        "Characters: " + " | ".join(f"{c['name']} ({c['role']}): {c['description']}; goals={c['goals']}; contradictions={c['contradictions']}" for c in characters),
        f"Preceding approved chapter summary: {preceding}",
        "Unresolved continuity facts: " + (" | ".join(f["fact"] for f in facts) or "None."),
        "Author decisions: " + (" | ".join(d["decision"] for d in decisions) or "None."),
    ])

