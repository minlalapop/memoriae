"""expériences composées et participants fictifs

Revision ID: 9f4a2c7d1e30
Revises: c42f9bd1a110
"""

from collections.abc import Sequence
import json
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "9f4a2c7d1e30"
down_revision: str | Sequence[str] | None = "c42f9bd1a110"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("prenom", sa.String(200), nullable=True))
    op.add_column(
        "patients",
        sa.Column("est_fictif", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("patients", sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.add_column("experiences", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("participant_access", sa.Column("patient_id", sa.String(36)))
    op.add_column(
        "participant_access",
        sa.Column("est_fictif", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_participant_access_patient_id", "participant_access", ["patient_id"])
    with op.batch_alter_table("participant_access") as batch:
        batch.create_foreign_key(
            "fk_participant_access_patient_id", "patients", ["patient_id"], ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "etapes_experience",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experience_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("test_type", sa.String(50), nullable=False),
        sa.Column("protocol_version", sa.String(20), nullable=False),
        sa.Column("parametres", sa.JSON(), nullable=False),
        sa.Column("seed_offset", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["experience_id"], ["experiences.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("experience_id", "position", name="uq_etape_experience_position"),
    )
    op.create_index("ix_etapes_experience_experience_id", "etapes_experience", ["experience_id"])

    connection = op.get_bind()
    experiences = connection.execute(
        sa.text(
            "SELECT id, test_type, protocol_version, parametres "
            "FROM experiences"
        )
    ).mappings()
    for experience in experiences:
        parameters = experience["parametres"]
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        connection.execute(
            sa.text(
                "INSERT INTO etapes_experience "
                "(id, experience_id, position, test_type, protocol_version, parametres, seed_offset) "
                "VALUES (:id, :experience_id, 0, :test_type, :version, :parameters, 0)"
            ),
            {
                "id": str(uuid.uuid4()),
                "experience_id": experience["id"],
                "test_type": experience["test_type"],
                "version": experience["protocol_version"],
                "parameters": json.dumps(parameters),
            },
        )

    op.create_table(
        "executions_etape",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("participant_access_id", sa.String(36), nullable=False),
        sa.Column("etape_id", sa.String(36)),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["participant_access_id"], ["participant_access.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["etape_id"], ["etapes_experience.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions_test.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("participant_access_id", "position", name="uq_execution_position"),
        sa.UniqueConstraint("session_id", name="uq_execution_session"),
    )
    op.create_index(
        "ix_executions_etape_participant_access_id",
        "executions_etape",
        ["participant_access_id"],
    )
    op.create_index("ix_executions_etape_etape_id", "executions_etape", ["etape_id"])
    op.create_index("ix_executions_etape_session_id", "executions_etape", ["session_id"], unique=True)


def downgrade() -> None:
    op.drop_table("executions_etape")
    op.drop_table("etapes_experience")
    with op.batch_alter_table("participant_access") as batch:
        batch.drop_constraint("fk_participant_access_patient_id", type_="foreignkey")
    op.drop_index("ix_participant_access_patient_id", table_name="participant_access")
    op.drop_column("participant_access", "est_fictif")
    op.drop_column("participant_access", "patient_id")
    op.drop_column("experiences", "description")
    op.drop_column("patients", "archived_at")
    op.drop_column("patients", "est_fictif")
    op.drop_column("patients", "prenom")
