"""create board_posts

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "board_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_board_posts_id", "board_posts", ["id"])


def downgrade() -> None:
    op.drop_index("ix_board_posts_id", table_name="board_posts")
    op.drop_table("board_posts")
