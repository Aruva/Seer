"""add_shop_tables

Adds shop_products and shop_orders tables for the shop system.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-03-18 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None

UTC_NOW = sa.text("(now() at time zone 'utc')")


def upgrade() -> None:
    # Shop products table
    op.create_table(
        "shop_products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("seller_xid", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.String(length=32), nullable=False),
        sa.Column("image_url", sa.String(length=512), nullable=True),
        sa.Column("product_type", sa.String(length=16), nullable=False, server_default="physical"),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["guild_xid"], ["guilds.xid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_xid"], ["users.xid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shop_products_guild_xid", "shop_products", ["guild_xid"])
    op.create_index("ix_shop_products_seller_xid", "shop_products", ["seller_xid"])

    # Shop orders table
    op.create_table(
        "shop_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.Column("guild_xid", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("buyer_xid", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("channel_xid", sa.BigInteger(), nullable=True),
        sa.Column("message_xid", sa.BigInteger(), nullable=True),
        sa.Column("payment_ref", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["guild_xid"], ["guilds.xid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["shop_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_xid"], ["users.xid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shop_orders_guild_xid", "shop_orders", ["guild_xid"])
    op.create_index("ix_shop_orders_product_id", "shop_orders", ["product_id"])
    op.create_index("ix_shop_orders_buyer_xid", "shop_orders", ["buyer_xid"])


def downgrade() -> None:
    op.drop_index("ix_shop_orders_buyer_xid", table_name="shop_orders")
    op.drop_index("ix_shop_orders_product_id", table_name="shop_orders")
    op.drop_index("ix_shop_orders_guild_xid", table_name="shop_orders")
    op.drop_table("shop_orders")
    op.drop_index("ix_shop_products_seller_xid", table_name="shop_products")
    op.drop_index("ix_shop_products_guild_xid", table_name="shop_products")
    op.drop_table("shop_products")
