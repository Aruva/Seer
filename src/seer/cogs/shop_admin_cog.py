from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from seer.database import db_session_manager
from seer.services import ShopService
from seer.settings import settings
from seer.utils import for_all_callbacks, is_guild

if TYPE_CHECKING:
    from seer import Seer

logger = logging.getLogger(__name__)


async def product_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[int]]:
    """Autocomplete for product IDs."""
    if not interaction.guild:
        return []

    async with db_session_manager():
        service = ShopService()
        products = await service.list_products(
            guild_xid=interaction.guild.id,
            active_only=False,
        )

    # Filter by name matching current input
    matching = [
        p for p in products
        if current.lower() in p.name.lower()
    ][:25]

    return [
        app_commands.Choice(name=p.name, value=p.id)
        for p in matching
    ]


async def seller_check(interaction: discord.Interaction) -> bool:
    """Check if user is the seller of a product."""
    # This is a simple check - in production you might want more sophisticated permissions
    return True


@for_all_callbacks(app_commands.check(is_guild))
class ShopAdminCog(commands.Cog):
    """Commands for managing shop products and orders."""

    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    shopadmin_group = app_commands.Group(
        name="shopadmin",
        description="Manage shop products and orders (sellers only).",
    )

    # ── /shopadmin add ─────────────────────────────────────────────────────

    @shopadmin_group.command(
        name="add",
        description="Add a new product to your shop.",
    )
    @app_commands.describe(
        name="Product name",
        price="Price (e.g., '$25' or 'Free')",
        description="Optional product description",
        product_type="Type: 'physical', 'digital', or 'both' (default: physical)",
        stock="Stock count (-1 for unlimited, default: -1)",
        image_url="Optional image URL",
        category="Optional category for organization",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        price: str,
        description: str | None = None,
        product_type: str | None = None,
        stock: int | None = None,
        image_url: str | None = None,
        category: str | None = None,
    ) -> None:
        """Add a new product."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        if product_type is None:
            product_type = "physical"
        if product_type not in ("physical", "digital", "both"):
            await interaction.followup.send(
                "Product type must be 'physical', 'digital', or 'both'."
            )
            return

        if stock is None:
            stock = -1

        async with db_session_manager():
            service = ShopService()
            product = await service.create_product(
                guild_xid=interaction.guild.id,
                seller_xid=interaction.user.id,
                name=name,
                price=price,
                description=description,
                product_type=product_type,
                stock=stock,
                image_url=image_url,
                category=category,
            )

        embed = discord.Embed(
            title="Product Added!",
            color=discord.Color.green(),
        )
        embed.add_field(name="Product ID", value=str(product.id), inline=False)
        embed.add_field(name="Name", value=product.name, inline=False)
        embed.add_field(name="Price", value=product.price, inline=True)
        embed.add_field(name="Type", value=product.product_type, inline=True)
        embed.add_field(
            name="Stock",
            value="Unlimited" if product.stock == -1 else str(product.stock),
            inline=True,
        )
        await interaction.followup.send(embed=embed)

    # ── /shopadmin edit ────────────────────────────────────────────────────

    @shopadmin_group.command(
        name="edit",
        description="Edit an existing product.",
    )
    @app_commands.describe(
        product_id="The product ID to edit",
        name="New product name",
        price="New price",
        description="New description",
        stock="New stock count",
        image_url="New image URL",
        category="New category",
    )
    @app_commands.autocomplete(product_id=product_autocomplete)
    async def edit(
        self,
        interaction: discord.Interaction,
        product_id: int,
        name: str | None = None,
        price: str | None = None,
        description: str | None = None,
        stock: int | None = None,
        image_url: str | None = None,
        category: str | None = None,
    ) -> None:
        """Edit a product."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        async with db_session_manager():
            service = ShopService()
            product = await service.get_product(product_id)

            if product is None:
                await interaction.followup.send("Product not found.")
                return

            if product.seller_xid != interaction.user.id:
                await interaction.followup.send(
                    "You can only edit your own products."
                )
                return

            updates = {}
            if name:
                updates["name"] = name
            if price:
                updates["price"] = price
            if description is not None:
                updates["description"] = description
            if stock is not None:
                updates["stock"] = stock
            if image_url is not None:
                updates["image_url"] = image_url
            if category is not None:
                updates["category"] = category

            product = await service.update_product(product_id, **updates)

        embed = discord.Embed(
            title="Product Updated!",
            color=discord.Color.green(),
        )
        embed.add_field(name="Product ID", value=str(product.id), inline=False)
        embed.add_field(name="Name", value=product.name, inline=False)
        embed.add_field(name="Price", value=product.price, inline=True)
        embed.add_field(name="Type", value=product.product_type, inline=True)
        embed.add_field(
            name="Stock",
            value="Unlimited" if product.stock == -1 else str(product.stock),
            inline=True,
        )
        await interaction.followup.send(embed=embed)

    # ── /shopadmin remove ──────────────────────────────────────────────────

    @shopadmin_group.command(
        name="remove",
        description="Deactivate a product listing.",
    )
    @app_commands.describe(
        product_id="The product ID to remove",
    )
    @app_commands.autocomplete(product_id=product_autocomplete)
    async def remove(
        self,
        interaction: discord.Interaction,
        product_id: int,
    ) -> None:
        """Remove a product."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        async with db_session_manager():
            service = ShopService()
            product = await service.get_product(product_id)

            if product is None:
                await interaction.followup.send("Product not found.")
                return

            if product.seller_xid != interaction.user.id:
                await interaction.followup.send(
                    "You can only remove your own products."
                )
                return

            success = await service.deactivate_product(product_id)

        if success:
            await interaction.followup.send(
                f"Product **{product.name}** has been removed."
            )
        else:
            await interaction.followup.send("Could not remove product.")

    # ── /shopadmin restock ─────────────────────────────────────────────────

    @shopadmin_group.command(
        name="restock",
        description="Add stock to a product.",
    )
    @app_commands.describe(
        product_id="The product ID to restock",
        quantity="Number of items to add to stock",
    )
    @app_commands.autocomplete(product_id=product_autocomplete)
    async def restock(
        self,
        interaction: discord.Interaction,
        product_id: int,
        quantity: int,
    ) -> None:
        """Restock a product."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        if quantity < 1:
            await interaction.followup.send("Quantity must be at least 1.")
            return

        async with db_session_manager():
            service = ShopService()
            product = await service.get_product(product_id)

            if product is None:
                await interaction.followup.send("Product not found.")
                return

            if product.seller_xid != interaction.user.id:
                await interaction.followup.send(
                    "You can only manage your own products."
                )
                return

            # Add to stock (if unlimited, keep it unlimited)
            if product.stock != -1:
                new_stock = product.stock + quantity
                product = await service.update_product(
                    product_id, stock=new_stock
                )
            else:
                new_stock = -1

        await interaction.followup.send(
            f"Restocked **{product.name}** with {quantity} items. "
            f"New stock: {'Unlimited' if new_stock == -1 else new_stock}"
        )

    # ── /shopadmin fulfill ─────────────────────────────────────────────────

    @shopadmin_group.command(
        name="fulfill",
        description="Mark an order as shipped/fulfilled.",
    )
    @app_commands.describe(
        order_id="The order ID to fulfill",
    )
    async def fulfill(
        self,
        interaction: discord.Interaction,
        order_id: int,
    ) -> None:
        """Fulfill an order."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        async with db_session_manager():
            service = ShopService()
            order = await service.get_order(order_id)

            if order is None:
                await interaction.followup.send("Order not found.")
                return

            # Get product to check seller
            product = await service.get_product(order.product_id)
            if product is None or product.seller_xid != interaction.user.id:
                await interaction.followup.send(
                    "You can only fulfill your own orders."
                )
                return

            order = await service.update_order_status(order_id, "shipped")

        embed = discord.Embed(
            title="Order Fulfilled",
            color=discord.Color.green(),
        )
        embed.add_field(name="Order ID", value=str(order.id), inline=False)
        embed.add_field(name="Buyer", value=f"<@{order.buyer_xid}>", inline=False)
        embed.add_field(name="Status", value=order.status.title(), inline=False)
        await interaction.followup.send(embed=embed)

        # Try to notify buyer
        try:
            buyer = await self.bot.fetch_user(order.buyer_xid)
            buyer_embed = discord.Embed(
                title="Order Shipped!",
                description=f"Your order #{order.id} has been shipped.",
                color=discord.Color.green(),
            )
            await buyer.send(embed=buyer_embed)
        except (discord.Forbidden, discord.NotFound):
            logger.warning(
                "Could not notify buyer %s about order %s",
                order.buyer_xid,
                order.id,
            )

    # ── /shopadmin cancel ──────────────────────────────────────────────────

    @shopadmin_group.command(
        name="cancel",
        description="Cancel an order.",
    )
    @app_commands.describe(
        order_id="The order ID to cancel",
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        order_id: int,
    ) -> None:
        """Cancel an order."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        async with db_session_manager():
            service = ShopService()
            order = await service.get_order(order_id)

            if order is None:
                await interaction.followup.send("Order not found.")
                return

            # Get product to check seller
            product = await service.get_product(order.product_id)
            if product is None or product.seller_xid != interaction.user.id:
                await interaction.followup.send(
                    "You can only cancel your own orders."
                )
                return

            # Restore stock if product exists
            if product.stock != -1:
                new_stock = product.stock + order.quantity
                await service.update_product(product.id, stock=new_stock)

            order = await service.update_order_status(order_id, "cancelled")

        await interaction.followup.send(
            f"Order **#{order.id}** has been cancelled."
        )

    # ── /shopadmin orders ──────────────────────────────────────────────────

    @shopadmin_group.command(
        name="orders",
        description="View all orders for your products.",
    )
    @app_commands.describe(
        status="Filter by status (pending, confirmed, paid, shipped, delivered, cancelled)",
    )
    async def orders(
        self,
        interaction: discord.Interaction,
        status: str | None = None,
    ) -> None:
        """View seller's orders."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        async with db_session_manager():
            service = ShopService()
            orders_list = await service.get_seller_orders(
                guild_xid=interaction.guild.id,
                seller_xid=interaction.user.id,
                status=status,
            )

        if not orders_list:
            status_text = f" with status '{status}'" if status else ""
            await interaction.followup.send(
                f"You have no orders{status_text}."
            )
            return

        embeds = []
        for order in orders_list:
            product = await service.get_product(order.product_id)
            if product is None:
                continue

            embed = discord.Embed(
                title=f"Order #{order.id}",
                color=discord.Color.blurple(),
            )
            embed.add_field(
                name="Buyer",
                value=f"<@{order.buyer_xid}>",
                inline=False,
            )
            embed.add_field(
                name="Product",
                value=product.name,
                inline=False,
            )
            embed.add_field(
                name="Quantity",
                value=str(order.quantity),
                inline=True,
            )
            embed.add_field(
                name="Status",
                value=order.status.title(),
                inline=True,
            )
            embed.add_field(
                name="Placed At",
                value=f"<t:{int(order.created_at.timestamp())}:F>",
                inline=False,
            )
            embeds.append(embed)

        # Send embeds in chunks of 10
        for i in range(0, len(embeds), 10):
            chunk = embeds[i : i + 10]
            if i == 0:
                await interaction.followup.send(embeds=chunk)
            else:
                await interaction.followup.send(embeds=chunk)

    # ── /shopadmin post ────────────────────────────────────────────────────

    @shopadmin_group.command(
        name="post",
        description="Post a product listing to a channel.",
    )
    @app_commands.describe(
        product_id="The product ID to post",
        channel="The channel to post to (optional, defaults to current channel)",
    )
    @app_commands.autocomplete(product_id=product_autocomplete)
    async def post(
        self,
        interaction: discord.Interaction,
        product_id: int,
        channel: discord.TextChannel | None = None,
    ) -> None:
        """Post a product listing."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        if channel is None:
            channel = interaction.channel  # type: ignore

        async with db_session_manager():
            service = ShopService()
            product = await service.get_product(product_id)

            if product is None:
                await interaction.followup.send("Product not found.")
                return

            if product.seller_xid != interaction.user.id:
                await interaction.followup.send(
                    "You can only post your own products."
                )
                return

        from seer.views import ShopView

        # Create embed
        embed = discord.Embed(
            title=product.name,
            description=product.description or "No description provided.",
            color=discord.Color.blurple(),
        )
        if product.image_url:
            embed.set_image(url=product.image_url)
        embed.add_field(
            name="Price",
            value=product.price,
            inline=True,
        )
        if product.stock == -1:
            stock_text = "Unlimited"
        else:
            stock_text = f"{product.stock} in stock"
        embed.add_field(
            name="Stock",
            value=stock_text,
            inline=True,
        )
        if product.category:
            embed.add_field(
                name="Category",
                value=product.category,
                inline=True,
            )
        embed.set_footer(text=f"Product ID: {product.id}")

        # Create view with order button
        view = ShopView(self.bot)
        view.product_id = product_id

        try:
            await channel.send(embed=embed, view=view)
            await interaction.followup.send(
                f"Product listing posted to {channel.mention}"
            )
        except discord.Forbidden:
            await interaction.followup.send(
                f"I don't have permission to post in {channel.mention}"
            )


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(ShopAdminCog(bot), guild=settings.GUILD_OBJECT)
