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


@for_all_callbacks(app_commands.check(is_guild))
class ShopCog(commands.Cog):
    """Commands for browsing and ordering from the shop."""

    def __init__(self, bot: Seer) -> None:
        self.bot = bot

    shop_group = app_commands.Group(
        name="shop",
        description="Browse and order products from the server shop.",
    )

    # ── /shop list ─────────────────────────────────────────────────────────

    @shop_group.command(
        name="list",
        description="Browse products available in the server shop.",
    )
    @app_commands.describe(
        category="Optional category to filter by.",
    )
    async def list_products(
        self,
        interaction: discord.Interaction,
        category: str | None = None,
    ) -> None:
        """List all active products in the server shop."""
        assert interaction.guild is not None
        await interaction.response.defer()

        async with db_session_manager():
            service = ShopService()
            products = await service.list_products(
                guild_xid=interaction.guild.id,
                active_only=True,
                category=category,
            )

        if not products:
            await interaction.followup.send(
                "No products available in the shop." if not category
                else f"No products found in category '{category}'."
            )
            return

        embeds = []
        for product in products:
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
            embeds.append(embed)

        # Send embeds in chunks of 10 (Discord limit)
        for i in range(0, len(embeds), 10):
            chunk = embeds[i : i + 10]
            if i == 0:
                await interaction.followup.send(embeds=chunk)
            else:
                await interaction.followup.send(embeds=chunk)

    # ── /shop order ────────────────────────────────────────────────────────

    @shop_group.command(
        name="order",
        description="Place an order for a product.",
    )
    @app_commands.describe(
        product_id="The product ID to order.",
        quantity="How many to order (default: 1).",
        note="Optional note for the seller.",
    )
    async def order(
        self,
        interaction: discord.Interaction,
        product_id: int,
        quantity: int | None = None,
        note: str | None = None,
    ) -> None:
        """Place an order for a product."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        if quantity is None:
            quantity = 1
        if quantity < 1:
            await interaction.followup.send("Quantity must be at least 1.")
            return

        async with db_session_manager():
            service = ShopService()
            product = await service.get_product(product_id)

            if product is None:
                await interaction.followup.send("Product not found.")
                return

            if not product.active:
                await interaction.followup.send("This product is no longer available.")
                return

            # Check stock
            if product.stock != -1 and product.stock < quantity:
                await interaction.followup.send(
                    f"Not enough stock. {product.stock} available."
                )
                return

            # Create order
            order = await service.create_order(
                guild_xid=interaction.guild.id,
                product_id=product_id,
                buyer_xid=interaction.user.id,
                quantity=quantity,
                note=note,
                channel_xid=interaction.channel_id,
            )

            if order is None:
                await interaction.followup.send(
                    "Could not create order. Please try again."
                )
                return

            # Send confirmation to buyer
            await interaction.followup.send(
                f"Order placed! **Order ID: {order.id}**\n"
                f"Contact the seller for payment instructions."
            )

            # Try to DM the buyer
            try:
                buyer_embed = discord.Embed(
                    title="Order Confirmation",
                    description=f"You've placed an order in {interaction.guild.name}",
                    color=discord.Color.green(),
                )
                buyer_embed.add_field(
                    name="Order ID",
                    value=str(order.id),
                    inline=False,
                )
                buyer_embed.add_field(
                    name="Product",
                    value=product.name,
                    inline=False,
                )
                buyer_embed.add_field(
                    name="Price",
                    value=product.price,
                    inline=False,
                )
                buyer_embed.add_field(
                    name="Quantity",
                    value=str(order.quantity),
                    inline=False,
                )
                if note:
                    buyer_embed.add_field(
                        name="Your Note",
                        value=note,
                        inline=False,
                    )
                buyer_embed.set_footer(
                    text="Status: Pending seller confirmation"
                )
                await interaction.user.send(embed=buyer_embed)
            except discord.Forbidden:
                logger.warning(
                    "Could not DM buyer %s for order %s",
                    interaction.user.id,
                    order.id,
                )

            # Try to DM the seller
            try:
                seller = await self.bot.fetch_user(product.seller_xid)
                seller_embed = discord.Embed(
                    title="New Order!",
                    description=f"Order ID: {order.id}",
                    color=discord.Color.gold(),
                )
                seller_embed.add_field(
                    name="Buyer",
                    value=f"<@{interaction.user.id}>",
                    inline=False,
                )
                seller_embed.add_field(
                    name="Product",
                    value=product.name,
                    inline=False,
                )
                seller_embed.add_field(
                    name="Quantity",
                    value=str(order.quantity),
                    inline=False,
                )
                seller_embed.add_field(
                    name="Price",
                    value=product.price,
                    inline=False,
                )
                if note:
                    seller_embed.add_field(
                        name="Buyer Note",
                        value=note,
                        inline=False,
                    )
                seller_embed.add_field(
                    name="Guild",
                    value=interaction.guild.name,
                    inline=False,
                )
                seller_embed.set_footer(
                    text="Use /shopadmin commands to manage orders."
                )
                await seller.send(embed=seller_embed)
            except (discord.Forbidden, discord.NotFound):
                logger.warning(
                    "Could not DM seller %s for order %s",
                    product.seller_xid,
                    order.id,
                )

    # ── /shop status ───────────────────────────────────────────────────────

    @shop_group.command(
        name="status",
        description="Check the status of your orders.",
    )
    @app_commands.describe(
        order_id="Optional order ID to check. Shows all your orders if not provided.",
    )
    async def status(
        self,
        interaction: discord.Interaction,
        order_id: int | None = None,
    ) -> None:
        """Check order status."""
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True)

        async with db_session_manager():
            service = ShopService()

            if order_id:
                order = await service.get_order(order_id)
                if order is None or order.buyer_xid != interaction.user.id:
                    await interaction.followup.send("Order not found.")
                    return

                product = await service.get_product(order.product_id)
                if product is None:
                    await interaction.followup.send("Product not found.")
                    return

                embed = discord.Embed(
                    title=f"Order #{order.id}",
                    color=discord.Color.blurple(),
                )
                embed.add_field(
                    name="Product",
                    value=product.name,
                    inline=False,
                )
                embed.add_field(
                    name="Quantity",
                    value=str(order.quantity),
                    inline=False,
                )
                embed.add_field(
                    name="Status",
                    value=order.status.title(),
                    inline=False,
                )
                embed.add_field(
                    name="Placed At",
                    value=f"<t:{int(order.created_at.timestamp())}:F>",
                    inline=False,
                )
                if order.note:
                    embed.add_field(
                        name="Your Note",
                        value=order.note,
                        inline=False,
                    )
                if order.payment_ref:
                    embed.add_field(
                        name="Payment Reference",
                        value=order.payment_ref,
                        inline=False,
                    )
                await interaction.followup.send(embed=embed)
            else:
                # Show all orders for this user in this guild
                orders = await service.list_orders(
                    guild_xid=interaction.guild.id,
                    buyer_xid=interaction.user.id,
                )

                if not orders:
                    await interaction.followup.send("You have no orders in this server.")
                    return

                embeds = []
                for order in orders:
                    product = await service.get_product(order.product_id)
                    if product is None:
                        continue

                    embed = discord.Embed(
                        title=f"Order #{order.id}",
                        color=discord.Color.blurple(),
                    )
                    embed.add_field(
                        name="Product",
                        value=product.name,
                        inline=False,
                    )
                    embed.add_field(
                        name="Status",
                        value=order.status.title(),
                        inline=True,
                    )
                    embed.add_field(
                        name="Quantity",
                        value=str(order.quantity),
                        inline=True,
                    )
                    embed.set_footer(text=f"ID: {order.id}")
                    embeds.append(embed)

                # Send embeds in chunks of 10
                for i in range(0, len(embeds), 10):
                    chunk = embeds[i : i + 10]
                    if i == 0:
                        await interaction.followup.send(embeds=chunk)
                    else:
                        await interaction.followup.send(embeds=chunk)


async def setup(bot: Seer) -> None:  # pragma: no cover
    await bot.add_cog(ShopCog(bot), guild=settings.GUILD_OBJECT)
