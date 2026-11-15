"""résultats computationnels

Revision ID: b8e31a6c4f20
Revises: 9f4a2c7d1e30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8e31a6c4f20"
down_revision: str | Sequence[str] | None = "9f4a2c7d1e30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executions_modele",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("protocol_version", sa.String(50), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("statut", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiences.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_executions_modele_experiment_id", "executions_modele", ["experiment_id"])
    op.create_index("ix_executions_modele_model_id", "executions_modele", ["model_id"])
    op.create_table(
        "resultats_modele",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("execution_id", sa.String(36), nullable=False),
        sa.Column("essai_index", sa.Integer(), nullable=False),
        sa.Column("stimulus_id", sa.String(100), nullable=False),
        sa.Column("predicted_stimulus_id", sa.String(100), nullable=False),
        sa.Column("correcte", sa.Boolean(), nullable=False),
        sa.Column("mse", sa.Float(), nullable=False),
        sa.Column("mesures", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["executions_modele.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_resultats_modele_execution_id", "resultats_modele", ["execution_id"])
    op.create_index("ix_resultats_modele_stimulus_id", "resultats_modele", ["stimulus_id"])


def downgrade() -> None:
    op.drop_table("resultats_modele")
    op.drop_table("executions_modele")
