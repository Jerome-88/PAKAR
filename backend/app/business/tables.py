"""Business resources share auth and infrastructure, with their own provenance."""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Table, Text, text
from sqlalchemy.dialects.postgresql import JSONB

from ..database import metadata

provider_spend_accounts = Table(
    "provider_spend_accounts", metadata,
    Column("id", String(64), primary_key=True),
    Column("available_usd", Numeric(24, 12), nullable=False),
)

provider_spend_reservations = Table(
    "provider_spend_reservations", metadata,
    Column("id", String(160), primary_key=True),
    Column("account_id", String(64), ForeignKey("provider_spend_accounts.id"), nullable=False),
    Column("ceiling_usd", Numeric(24, 12), nullable=False),
    Column("charged_usd", Numeric(24, 12), nullable=True),
)


business_projects = Table(
    "business_projects", metadata,
    Column("id", String, primary_key=True),
    Column("owner_user_id", String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("context", JSONB, nullable=False),
    Column("revision", Integer, nullable=False, server_default="1"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("idempotency_key", String(128), nullable=True),
)
Index("business_projects_owner_key", business_projects.c.owner_user_id, business_projects.c.idempotency_key, unique=True)

business_documents = Table(
    "business_documents", metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False),
    Column("name", String, nullable=False),
    Column("storage_key", Text, nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("status", String, nullable=False),
    Column("content", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
Index("business_documents_project", business_documents.c.project_id)

business_claims = Table(
    "business_claims", metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False),
    Column("document_id", String, ForeignKey("business_documents.id", ondelete="CASCADE"), nullable=False),
    Column("content", JSONB, nullable=False),
)
Index("business_claims_project", business_claims.c.project_id)

business_personas = Table(
    "business_personas", metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False),
    Column("content", JSONB, nullable=False),
)
Index("business_personas_project", business_personas.c.project_id)

business_analyses = Table(
    "business_analyses", metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False),
    Column("baseline_id", String, ForeignKey("business_analyses.id", ondelete="CASCADE"), nullable=True),
    Column("status", String, nullable=False),
    Column("stage", String, nullable=False),
    Column("input_snapshot", JSONB, nullable=False),
    Column("result", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("idempotency_key", String(128), nullable=True),
)
Index("business_analyses_project_key", business_analyses.c.project_id, business_analyses.c.idempotency_key, unique=True)

business_events = Table(
    "business_events", metadata,
    Column("analysis_id", String, ForeignKey("business_analyses.id", ondelete="CASCADE"), primary_key=True),
    Column("sequence", Integer, primary_key=True),
    Column("type", String, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

business_ideas = Table(
    "business_ideas", metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False),
    Column("title", String(160), nullable=False),
    Column("version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("idempotency_key", String(128), nullable=False),
)
Index("business_ideas_project_key", business_ideas.c.project_id, business_ideas.c.idempotency_key, unique=True)

business_idea_revisions = Table(
    "business_idea_revisions", metadata,
    Column("id", String, primary_key=True),
    Column("idea_id", String, ForeignKey("business_ideas.id", ondelete="CASCADE"), nullable=False),
    Column("project_id", String, ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("content", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("idempotency_key", String(128), nullable=False),
)
Index("business_idea_revisions_version", business_idea_revisions.c.idea_id, business_idea_revisions.c.version, unique=True)
Index("business_idea_revisions_key", business_idea_revisions.c.project_id, business_idea_revisions.c.idempotency_key, unique=True)

business_chat_turns = Table(
    "business_chat_turns", metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, ForeignKey("business_projects.id", ondelete="CASCADE"), nullable=False),
    Column("sequence", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("request", JSONB, nullable=False),
    Column("input_snapshot", JSONB, nullable=False),
    Column("response", JSONB, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("idempotency_key", String(128), nullable=False),
)
Index("business_chat_turns_sequence", business_chat_turns.c.project_id, business_chat_turns.c.sequence, unique=True)
Index("business_chat_turns_key", business_chat_turns.c.project_id, business_chat_turns.c.idempotency_key, unique=True)
