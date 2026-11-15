"""expériences publiées et accès pseudonymes

Revision ID: c42f9bd1a110
Revises: 75d39e02926b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c42f9bd1a110"
down_revision: str | Sequence[str] | None = "75d39e02926b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experiences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nom", sa.String(200), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("test_type", sa.String(50), nullable=False),
        sa.Column("protocol_version", sa.String(20), nullable=False),
        sa.Column("parametres", sa.JSON(), nullable=False),
        sa.Column("seed_base", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_experiences_code", "experiences", ["code"], unique=True)
    op.create_table(
        "researcher_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(200), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_researcher_sessions_token_hash",
        "researcher_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_researcher_sessions_expires_at",
        "researcher_sessions",
        ["expires_at"],
    )
    op.create_table(
        "participant_access",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("pseudonyme", sa.String(50), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_test.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_participant_access_experiment_id", "participant_access", ["experiment_id"])
    op.create_index("ix_participant_access_session_id", "participant_access", ["session_id"], unique=True)
    op.create_index("ix_participant_access_token_hash", "participant_access", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("participant_access")
    op.drop_table("researcher_sessions")
    op.drop_table("experiences")
