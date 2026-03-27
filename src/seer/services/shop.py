from __future__ import annotations

from asgiref.sync import sync_to_async

from seer.database import DatabaseSession
from seer.models import ShopOrder, ShopProduct


class ShopService:
    """Service for managing shop products and orders."""

    @sync_to_async()
    def create_product(
        self,
        guild_xid: int,
        seller_xid: int,
        name: str,
        price: str,
        description: str | None = None,
        product_type: str = "physical",
        stock: int = -1,
        image_url: str | None = None,
        category: str | None = None,
    ) -> ShopProduct:
        """Create a new product listing."""
        product = ShopProduct(
            guild_xid=guild_xid,
            seller_xid=seller_xid,
            name=name,
            price=price,
            description=description,
            product_type=product_type,
            stock=stock,
            image_url=image_url,
            category=category,
            active=True,
        )
        DatabaseSession.add(product)
        DatabaseSession.flush()
        return product

    @sync_to_async()
    def get_product(self, product_id: int) -> ShopProduct | None:
        """Get a product by ID."""
        return (
            DatabaseSession.query(ShopProduct)
            .filter(ShopProduct.id == product_id)
            .one_or_none()
        )

    @sync_to_async()
    def list_products(
        self,
        guild_xid: int,
        active_only: bool = True,
        category: str | None = None,
    ) -> list[ShopProduct]:
        """List products in a guild."""
        query = DatabaseSession.query(ShopProduct).filter(
            ShopProduct.guild_xid == guild_xid
        )
        if active_only:
            query = query.filter(ShopProduct.active == True)  # noqa: E712
        if category:
            query = query.filter(ShopProduct.category == category)
        return query.order_by(ShopProduct.name).all()

    @sync_to_async()
    def update_product(self, product_id: int, **kwargs) -> ShopProduct | None:
        """Update a product."""
        product = (
            DatabaseSession.query(ShopProduct)
            .filter(ShopProduct.id == product_id)
            .one_or_none()
        )
        if product is None:
            return None
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        DatabaseSession.flush()
        return product

    @sync_to_async()
    def deactivate_product(self, product_id: int) -> bool:
        """Deactivate a product listing."""
        product = (
            DatabaseSession.query(ShopProduct)
            .filter(ShopProduct.id == product_id)
            .one_or_none()
        )
        if product is None:
            return False
        product.active = False
        DatabaseSession.flush()
        return True

    @sync_to_async()
    def create_order(
        self,
        guild_xid: int,
        product_id: int,
        buyer_xid: int,
        quantity: int = 1,
        note: str | None = None,
        channel_xid: int | None = None,
        message_xid: int | None = None,
    ) -> ShopOrder | None:
        """Create an order, checking stock and decrementing if applicable."""
        product = (
            DatabaseSession.query(ShopProduct)
            .filter(ShopProduct.id == product_id)
            .one_or_none()
        )
        if product is None:
            return None

        # Check stock
        if product.stock != -1 and product.stock < quantity:
            return None

        # Decrement stock if not unlimited
        if product.stock != -1:
            product.stock -= quantity

        # Create order
        order = ShopOrder(
            guild_xid=guild_xid,
            product_id=product_id,
            buyer_xid=buyer_xid,
            quantity=quantity,
            note=note,
            channel_xid=channel_xid,
            message_xid=message_xid,
            status="pending",
        )
        DatabaseSession.add(order)
        DatabaseSession.flush()
        return order

    @sync_to_async()
    def get_order(self, order_id: int) -> ShopOrder | None:
        """Get an order by ID."""
        return (
            DatabaseSession.query(ShopOrder)
            .filter(ShopOrder.id == order_id)
            .one_or_none()
        )

    @sync_to_async()
    def list_orders(
        self,
        guild_xid: int,
        buyer_xid: int | None = None,
        seller_xid: int | None = None,
        status: str | None = None,
    ) -> list[ShopOrder]:
        """List orders in a guild."""
        query = DatabaseSession.query(ShopOrder).filter(
            ShopOrder.guild_xid == guild_xid
        )
        if buyer_xid:
            query = query.filter(ShopOrder.buyer_xid == buyer_xid)
        if status:
            query = query.filter(ShopOrder.status == status)
        if seller_xid:
            # Filter by seller via product
            query = query.join(ShopProduct).filter(
                ShopProduct.seller_xid == seller_xid
            )
        return query.order_by(ShopOrder.created_at.desc()).all()

    @sync_to_async()
    def update_order_status(
        self,
        order_id: int,
        status: str,
        payment_ref: str | None = None,
    ) -> ShopOrder | None:
        """Update an order status."""
        order = (
            DatabaseSession.query(ShopOrder)
            .filter(ShopOrder.id == order_id)
            .one_or_none()
        )
        if order is None:
            return None
        order.status = status
        if payment_ref:
            order.payment_ref = payment_ref
        DatabaseSession.flush()
        return order

    @sync_to_async()
    def get_seller_orders(
        self,
        guild_xid: int,
        seller_xid: int,
        status: str | None = None,
    ) -> list[ShopOrder]:
        """Get all orders for a seller's products."""
        query = DatabaseSession.query(ShopOrder).filter(
            ShopOrder.guild_xid == guild_xid
        )
        query = query.join(ShopProduct).filter(
            ShopProduct.seller_xid == seller_xid
        )
        if status:
            query = query.filter(ShopOrder.status == status)
        return query.order_by(ShopOrder.created_at.desc()).all()
