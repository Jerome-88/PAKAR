"""Durable conservative reservations for paid business inference."""
from alembic import op

revision = "0017_provider_spending"
down_revision = "0016_business_conversation"
branch_labels = None
depends_on = None


def upgrade():
    from app.business.tables import provider_spend_accounts, provider_spend_reservations
    provider_spend_accounts.create(op.get_bind())
    provider_spend_reservations.create(op.get_bind())


def downgrade():
    op.drop_table("provider_spend_reservations")
    op.drop_table("provider_spend_accounts")
