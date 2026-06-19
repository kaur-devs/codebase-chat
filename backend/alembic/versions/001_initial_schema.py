"""initial schema with pgvector

Revision ID: 001
Revises: None
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("github_id", sa.BigInteger(), unique=True, index=True, nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text(), server_default=""),
        sa.Column("access_token_encrypted", sa.Text(), server_default=""),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("preferred_model", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "repos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("default_branch", sa.String(255), server_default="main"),
        sa.Column("file_count", sa.Integer(), server_default="0"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("readme_content", sa.Text(), nullable=True),
        sa.Column("file_tree", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repos.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("function_name", sa.String(255), nullable=True),
        sa.Column("class_name", sa.String(255), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=False),
        sa.Column("line_end", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("code_text", sa.Text(), nullable=False),
    )

    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(1024)")
    op.execute("CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repo_id", sa.Integer(), sa.ForeignKey("repos.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("title", sa.String(255), server_default="New conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("chunks")
    op.drop_table("repos")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
