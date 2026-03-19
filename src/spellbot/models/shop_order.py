from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import expression as sql

from .base import Base, now

UTC_NOW = "timezone('utc', now())"


class ShopOrder(Base):
    """An order placed for a shop product."""

    __tablename__ = "shop_orders"

    id = Column(
        Integer,
        autoincrement=True,
        primary_key=True,
        nullable=False,
        doc="Internal order ID",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=now,
        doc="When this order was placed",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=now,
        doc="When this order was last updated",
    )
    guild_xid = Column(
        BigInteger,
        ForeignKey("guilds.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord guild where order was placed",
    )
    product_id = Column(
        Integer,
        ForeignKey("shop_products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="ID of the product ordered",
    )
    buyer_xid = Column(
        BigInteger,
        ForeignKey("users.xid", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Discord user ID of the buyer",
    )
    quantity = Column(
        Integer,
        nullable=False,
        server_default="1",
        doc="Quantity ordered",
    )
    status = Column(
        String(16),
        nullable=False,
        server_default="pending",
        doc="Order status: pending, confirmed, paid, shipped, delivered, cancelled, refunded",
    )
    note = Column(
        Text,
        nullable=True,
        doc="Optional note from buyer",
    )
    channel_xid = Column(
        BigInteger,
        nullable=True,
        doc="Discord channel where the order was placed",
    )
    message_xid = Column(
        BigInteger,
        nullable=True,
        doc="Discord message ID of the order",
    )
    payment_ref = Column(
        String(128),
        nullable=True,
        doc="Payment reference (e.g., 'PayPal txn ABC123')",
    )
