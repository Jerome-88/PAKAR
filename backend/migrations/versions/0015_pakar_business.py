"""Add PAKAR business resources without altering legacy workflow artifacts."""
import sqlalchemy as sa
from alembic import op

revision = "0015_pakar_business"
down_revision = "0014_quick_demo"
branch_labels = None
depends_on = None


def upgrade():
    from app.business.tables import (
        business_projects, business_documents, business_claims, business_personas,
        business_analyses, business_events,
    )
    for table in (business_projects, business_documents, business_claims, business_personas, business_analyses, business_events):
        table.create(op.get_bind())
    op.alter_column("jobs", "simulation_id", existing_type=sa.String(), nullable=True)
    op.add_column("jobs", sa.Column("analysis_id", sa.String(), nullable=True))
    op.create_foreign_key("jobs_analysis_id_fkey", "jobs", "business_analyses", ["analysis_id"], ["id"], ondelete="CASCADE")
    op.create_index("jobs_analysis", "jobs", ["analysis_id"])
    op.create_check_constraint("jobs_exactly_one_target", "jobs", "(simulation_id IS NOT NULL) <> (analysis_id IS NOT NULL)")


def downgrade():
    # Business queue rows cannot become legacy simulation jobs.
    op.execute("DELETE FROM jobs WHERE analysis_id IS NOT NULL")
    op.drop_constraint("jobs_exactly_one_target", "jobs", type_="check")
    op.drop_index("jobs_analysis", table_name="jobs")
    op.drop_constraint("jobs_analysis_id_fkey", "jobs", type_="foreignkey")
    op.drop_column("jobs", "analysis_id")
    op.alter_column("jobs", "simulation_id", existing_type=sa.String(), nullable=False)
    for name in ("business_events", "business_analyses", "business_personas", "business_claims", "business_documents", "business_projects"):
        op.drop_table(name)
