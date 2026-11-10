"""Persistent project conversations and immutable idea revisions."""
import sqlalchemy as sa
from alembic import op

revision = "0016_business_conversation"
down_revision = "0015_pakar_business"
branch_labels = None
depends_on = None


def upgrade():
    from app.business.tables import business_ideas, business_idea_revisions, business_chat_turns
    for table in (business_ideas, business_idea_revisions, business_chat_turns):
        table.create(op.get_bind())
    op.add_column("jobs", sa.Column("business_chat_turn_id", sa.String(), nullable=True))
    op.create_foreign_key("jobs_business_chat_turn_fkey", "jobs", "business_chat_turns", ["business_chat_turn_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("jobs_exactly_one_target", "jobs", type_="check")
    op.create_check_constraint("jobs_exactly_one_target", "jobs", "num_nonnulls(simulation_id, analysis_id, business_chat_turn_id) = 1")


def downgrade():
    op.execute("DELETE FROM jobs WHERE business_chat_turn_id IS NOT NULL")
    op.drop_constraint("jobs_exactly_one_target", "jobs", type_="check")
    op.create_check_constraint("jobs_exactly_one_target", "jobs", "(simulation_id IS NOT NULL) <> (analysis_id IS NOT NULL)")
    op.drop_constraint("jobs_business_chat_turn_fkey", "jobs", type_="foreignkey")
    op.drop_column("jobs", "business_chat_turn_id")
    for name in ("business_chat_turns", "business_idea_revisions", "business_ideas"):
        op.drop_table(name)
