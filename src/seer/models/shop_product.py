from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import expression as sql

from .base import Base, now

UTC_NOW = "timezone('utc', now())"


class ShopProduct(Base):
    """A product listing for the shop system."""

    __tablename__ = "shop_products"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
        doc="Internal product ID",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=now,
        doc="When this product was created",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=now,
        doc="When this product was last updated",
    )
    guild_xid = Column(
        BigInteger,
        ForeignKey("guilds.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord guild this product belongs to",
    )
    seller_xid = Column(
        BigInteger,
        ForeignKey("users.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord user ID of the seller",
    )
    name = Column(
        String(128),
        nullable=False,
        doc="Product name",
    )
    description = Column(
        Text,
        nullable=True,
        doc="Product description",
    )
    price = Column(
        String(32),
        nullable=False,
        doc="Price as free text (e.g., '$25' or 'Free')",
    )
    image_url = Column(
        String(512),
        nullable=True,
        doc="Optional image URL for the product",
    )
    product_type = Column(
        String(16),
        nullable=False,
        server_default="physical",
        doc="Type of product: 'physical', 'digital', or 'both'",
    )
    stock = Column(
        Integer,
        nullable=False,
        server_default="-1",
        doc="Current stock count (-1 means unlimited for digital goods)",
    )
    active = Column(
        Boolean,
        nullable=False,
        server_default=sql.true(),
        doc="Whether this product is currently listed",
    )
    category = Column(
        String(64),
        nullable=True,
        doc="Optional category for organization",
    )
