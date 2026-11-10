"""User-authored ideas remain assumptions; chat never commits a revision."""
from typing import Literal
from pydantic import Field, model_validator
from .contracts import Contract

TARGETS = {
    "facilitator": "Fasilitator PAKAR", "market": "Market Agent", "finance": "Finance Agent",
    "legal": "Legal/Compliance Agent", "risk": "Risk Agent",
}


class IdeaInput(Contract):
    expected_revision: int = Field(ge=1)
    expected_version: int = Field(default=0, ge=0)
    title: str = Field(min_length=2, max_length=160)
    text: str = Field(default="", max_length=6000)
    document_ids: list[str] = Field(default_factory=list, max_length=5)
    source_turn_ids: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def has_content(self):
        if not self.text and not self.document_ids:
            raise ValueError("Tuliskan ide atau pilih dokumen ide")
        return self


class ChatInput(Contract):
    expected_revision: int = Field(ge=1)
    content: str = Field(min_length=2, max_length=4000)
    target: Literal["facilitator", "market", "finance", "legal", "risk"] = "facilitator"
    idea_revision_id: str | None = Field(default=None, max_length=100)
    analysis_id: str | None = Field(default=None, max_length=100)
    max_tokens: int = Field(default=24000, ge=4000, le=30000)


class ChatReply(Contract):
    answer: str = Field(min_length=1, max_length=4000)
    questions: list[str] = Field(default_factory=list, max_length=3)
    source_ids: list[str] = Field(default_factory=list, max_length=5)
    suggested_revision: str | None = Field(default=None, max_length=6000)

    @model_validator(mode="after")
    def bounded_questions(self):
        if any(not q.strip() or len(q) > 350 for q in self.questions):
            raise ValueError("Pertanyaan klarifikasi tidak valid")
        return self
