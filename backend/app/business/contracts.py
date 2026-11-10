from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BusinessContext(Contract):
    name: str = Field(min_length=2, max_length=160)
    industry: str = Field(min_length=2, max_length=100)
    region: str = Field(min_length=2, max_length=120)
    target_customer: str = Field(min_length=2, max_length=300)
    decision_question: str = Field(min_length=10, max_length=2000)
    business_model: str = Field(default="", max_length=1000)
    value_proposition: str = Field(default="", max_length=1000)
    data_classification: Literal["public", "synthetic", "non_confidential"]


class Claim(Contract):
    id: str
    quote: str = Field(min_length=1, max_length=6000)
    normalized_text: str = Field(min_length=1, max_length=6000)
    classification: Literal["supplied_fact", "assumption", "calculation", "opinion", "forecast"] = "assumption"
    variable: Literal["selling_price", "variable_cost", "fixed_cost_monthly", "volume_monthly"] | None = None
    value: Decimal | None = Field(default=None, ge=0, le=Decimal("1e15"))
    unit: str | None = Field(default=None, max_length=100)
    period: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=120)
    source: dict = Field(default_factory=dict)
    review_status: Literal["pending", "approved", "rejected"] = "pending"
    evidence_status: Literal["VERIFIED", "PARTIAL", "CONFLICTING", "UNAVAILABLE", "STALE"] = "UNAVAILABLE"
    revision: int = Field(default=1, ge=1)


class ClaimPatch(Contract):
    expected_revision: int = Field(ge=1)
    normalized_text: str | None = Field(default=None, min_length=1, max_length=6000)
    classification: Literal["supplied_fact", "assumption", "calculation", "opinion", "forecast"] | None = None
    variable: Literal["selling_price", "variable_cost", "fixed_cost_monthly", "volume_monthly"] | None = None
    value: Decimal | None = Field(default=None, ge=0, le=Decimal("1e15"))
    unit: str | None = Field(default=None, max_length=100)
    period: str | None = Field(default=None, max_length=100)
    review_status: Literal["pending", "approved", "rejected"] | None = None


class Persona(Contract):
    id: str
    name: str = Field(min_length=2, max_length=160)
    role: Literal["operator", "customer", "supplier", "competitor", "employee", "regulator", "partner", "investor", "community"]
    stakeholder_type: Literal["direct", "indirect", "hidden"] = "direct"
    goals: list[str] = Field(min_length=1, max_length=8)
    motivations: list[str] = Field(default_factory=list, max_length=8)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    knowledge: list[str] = Field(default_factory=list, max_length=12)
    interests: list[str] = Field(default_factory=list, max_length=8)
    relationships: list[str] = Field(default_factory=list, max_length=30)
    provenance: dict = Field(default_factory=lambda: {"profile": "synthetic_hypothesis"})
    discovery_rationale: str = Field(default="", max_length=2000)
    active: bool = True
    reviewed: bool = False
    revision: int = Field(default=1, ge=1)

    @field_validator("goals", "motivations", "constraints", "knowledge", "interests", "relationships")
    @classmethod
    def bounded_text(cls, values):
        if any(not isinstance(value, str) or not value.strip() or len(value) > 1000 for value in values):
            raise ValueError("Setiap atribut persona harus berisi teks sepanjang 1–1000 karakter")
        return values


class PersonaPatch(Contract):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    goals: list[str] | None = Field(default=None, min_length=1, max_length=8)
    constraints: list[str] | None = Field(default=None, max_length=8)
    motivations: list[str] | None = Field(default=None, max_length=8)
    knowledge: list[str] | None = Field(default=None, max_length=12)
    interests: list[str] | None = Field(default=None, max_length=8)
    active: bool | None = None
    reviewed: bool | None = None


class Shock(Contract):
    kind: Literal["supplier_cost_increase", "competitor_price_cut", "regulation_change"]
    magnitude_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    effective_round: int = Field(default=2, ge=1, le=12)
    duration_rounds: int = Field(default=3, ge=1, le=12)
    region: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    response_strategy: Literal["observe", "match_price"] = "observe"
    announce_to_personas: bool = False


class AnalysisInput(Contract):
    expected_revision: int = Field(ge=1)
    public_brief: str = Field(default="", max_length=4000)
    engine: Literal["fixture", "oasis"] = "oasis"
    rounds: int = Field(default=4, ge=2, le=12)
    max_personas: int = Field(default=10, ge=2, le=24)
    max_events: int = Field(default=80, ge=3, le=300)
    max_tokens: int = Field(default=24000, ge=1000, le=300000)
    max_cost_usd: Decimal = Field(default=Decimal("0.03"), gt=0, le=Decimal("1"), allow_inf_nan=False)
    max_seconds: int = Field(default=300, ge=10, le=900)
    persona_turn_seconds: int = Field(default=60, ge=5, le=60)
    review_concurrency: int = Field(default=1, ge=1, le=2)
    seed: int = Field(default=42, ge=0, le=2147483647)
    interaction_mode: Literal["pairwise", "swarm"] = "pairwise"
    customer_count: int = Field(default=4, ge=2, le=6)
    discussion_policy: Literal["round-robin-v1", "reactive-v2"] = "round-robin-v1"
    followups_per_round: int = Field(default=2, ge=0, le=6)
    strict_trigger_reply: bool = False
    business_system_prompt: bool = False
    compact_dialogue: bool = False
    choice_dialogue: bool = False
    document_grounding: bool = False
    novelty_guard: bool = True
    adaptive_turns: bool = True


class QuickAnalysisInput(AnalysisInput):
    idea_revision_id: str | None = Field(default=None, max_length=100)
    rounds: int = Field(default=3, ge=2, le=12)
    max_personas: int = Field(default=8, ge=2, le=12)
    max_tokens: int = Field(default=100000, ge=1000, le=300000)
    interaction_mode: Literal["pairwise", "swarm"] = "swarm"
    discussion_policy: Literal["round-robin-v1", "reactive-v2"] = "reactive-v2"
    strict_trigger_reply: bool = True
    business_system_prompt: bool = True
    compact_dialogue: bool = True
    choice_dialogue: bool = True
    document_grounding: bool = True

    @model_validator(mode="after")
    def cohort_fits_budget(self):
        if self.interaction_mode == "swarm" and self.customer_count + 1 > self.max_personas:
            raise ValueError("Batas persona harus mencakup customer dan minimal satu pengelola")
        return self


class ScenarioInput(Contract):
    shock: Shock


class SpecialistReviewInput(Contract):
    max_tokens: int = Field(default=100000, ge=1000, le=100000)
    max_cost_usd: Decimal = Field(default=Decimal("0.01"), gt=0, le=Decimal("1"), allow_inf_nan=False)
    max_seconds: int = Field(default=300, ge=10, le=300)
    review_concurrency: int = Field(default=1, ge=1, le=2)
    retry_failed: bool = False
    recover_cancelled: bool = False


class BusinessAction(Contract):
    actor_id: str
    target_id: str
    kind: Literal["offer_terms", "accept_terms", "adjust_price", "express_concern", "request_information", "cooperate", "compete"]
    expected_version: int = Field(ge=0)
    parent_event_ids: list[str] = Field(default_factory=list, max_length=10)
    amount: Decimal | None = Field(default=None, gt=0, le=Decimal("1e15"))
    rationale: str = Field(min_length=3, max_length=1500)


class SwarmAction(Contract):
    actor_id: str
    target_id: str
    kind: Literal["post_message", "reply_message", "abstain", "offer_terms", "accept_terms", "adjust_price", "express_concern", "request_information", "cooperate", "compete"]
    expected_version: int = Field(ge=0)
    parent_event_ids: list[str] = Field(default_factory=list, max_length=10)
    amount: Decimal | None = Field(default=None, gt=0, le=Decimal("1e15"))
    rationale: str = Field(min_length=3, max_length=1500)
    visibility: Literal["public", "participants"] = "public"
    thread_id: str | None = None
    reply_to: str | None = None
    content: str = Field(default="", max_length=1200)
    stance: Literal["support", "oppose", "conditional", "undecided"] = "undecided"
    stance_reason: str = Field(default="", max_length=500)
    influenced_by_event_ids: list[str] = Field(default_factory=list, max_length=5)


class DialogueAction(SwarmAction):
    dialogue_act: Literal["statement", "question", "answer", "challenge", "clarification", "proposal", "abstain"]


class DialogueReply(Contract):
    content: str = Field(min_length=1, max_length=1000)
    stance: Literal["support", "oppose", "conditional", "undecided"]
    stance_reason: str = Field(min_length=1, max_length=240)


class DialogueProposal(DialogueReply):
    content: str = Field(max_length=1000)
    action: Literal["post_message", "reply_message", "abstain", "offer_terms", "accept_terms", "adjust_price"]
    target_id: str
    reply_to_message: int | None = Field(ge=1)
    dialogue_act: Literal["statement", "question", "answer", "challenge", "clarification", "proposal", "abstain"]
    amount: Decimal | None = Field(ge=0, le=Decimal("1e15"))


class DialogueChoice(DialogueReply):
    content: str = Field(max_length=1000)
    choice: str
    amount: Decimal | None = Field(ge=0, le=Decimal("1e15"))


class Finding(Contract):
    id: str
    title: str
    category: Literal["document", "evidence", "stakeholder", "interaction", "scenario"]
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    status: Literal["NEEDS_VALIDATION", "SUPPORTED", "CONFLICTING"] = "NEEDS_VALIDATION"
    origin: Literal["document", "evidence", "simulation", "scenario"]
    author: str
    claim_ids: list[str] = Field(default_factory=list)
    persona_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    calculation_ids: list[str] = Field(default_factory=list)
    reasoning: str
    confidence: Literal["low", "medium", "high"] = "low"
    evidence_gaps: list[str] = Field(default_factory=list)
    next_validation: str
    owner_suggestion: str
