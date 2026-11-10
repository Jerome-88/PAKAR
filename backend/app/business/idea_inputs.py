"""Reuse the document intake contract for immutable user-proposed text."""
import re
from ..documents import ExtractedDocument, TextSegment
from .intake import extract_claims


def idea_claims(revision):
    text = revision["content"]["text"]
    segments = tuple(TextSegment(m.group(), m.start(), m.end(), paragraph=i + 1) for i, m in enumerate(re.finditer(r"[^\n]+", text)) if m.group().strip())
    claims = extract_claims(revision["id"], ExtractedDocument(text, segments)) if segments else []
    for claim in claims:
        claim["source"].update(idea_revision_id=revision["id"], source_kind="user_proposed_assumption")
        claim["classification"] = "forecast" if claim["classification"] == "forecast" else "assumption"
    return claims


def public_idea(revision):
    return {"id": revision["id"], "idea_id": revision["idea_id"], "version": revision["version"], **revision["content"]}
