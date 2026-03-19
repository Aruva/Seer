from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import ui

from spellbot.database import db_session_manager
from spellbot.models import ShopProduct

from . import BaseView

if TYPE_CHECKING:
    from spellbot import SpellBot

logger = logging.getLogger(__name__)


class ShopView(BaseView):
    """Persistent view for shop product order button."""

    def __init__(self, bot: SpellBot) -> None:
        super().__init__(bot)
        self.product_id: int | None = None

    @ui.button(
        custom_id="shop_order_btn",
        emoji="🛒",
        label="Order",
        style=discord.ButtonStyle.green,
    )
    async def order_button(
        self,
        interaction: discord.Interaction,
        button: ui.Button[ShopView],
    ) -> None:
        """Handle order button click."""
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        # Extract product_id from message content or custom data
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            product_id_str = embed.footer.text if embed.footer else None
            if product_id_str and product_id_str.startswith("Product ID: "):
                try:
                    product_id = int(product_id_str.replace("Product ID: ", ""))
                except ValueError:
                    await interaction.response.send_message(
                        "Error: Could not identify product.",
                        ephemeral=True,
                    )
                    return
            else:
                await interaction.response.send_message(
                    "Error: Could not identify product.",
                    ephemeral=True,
                )
                return
        else:
            await interaction.response.send_message(
                "Error: Could not identify product.",
                ephemeral=True,
            )
            return

        async with db_session_manager():
            from spellbot.services import ShopService

            service = ShopService()
            product = await service.get_product(product_id)

            if product is None:
                await interaction.response.send_message(
                    "Product not found.",
                    ephemeral=True,
                )
                return

            if not product.active:
                await interaction.response.send_message(
                    "This product is no longer available.",
                    ephemeral=True,
                )
                return

            # Check stock
            if product.stock == 0:
                await interaction.response.send_message(
                    "This product is out of stock.",
                    ephemeral=True,
                )
                return

            # Create order
            order = await service.create_order(
                guild_xid=interaction.guild.id,
                product_id=product_id,
                buyer_xid=interaction.user.id,
                quantity=1,
                channel_xid=interaction.channel_id,
                message_xid=interaction.message.id if interaction.message else None,
            )

            if order is None:
                await interaction.response.send_message(
                    "Could not create order. Product may be out of stock.",
                    ephemeral=True,
                )
                return

            # Acknowledge the interaction
            await interaction.response.send_message(
                f"Order placed! Order ID: {order.id}\n"
                f"Please contact the seller for payment instructions.",
                ephemeral=True,
            )

            # Try to DM the buyer
            try:
                buyer_embed = discord.Embed(
                    title="Order Confirmation",
                    description=f"You've placed an order for **{product.name}**",
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
                buyer_embed.add_field(
                    name="Status",
                    value=order.status,
                    inline=False,
                )
                buyer_embed.set_footer(
                    text="Please wait for the seller to confirm your order."
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
                    description=f"You have a new order for **{product.name}**",
                    color=discord.Color.gold(),
                )
                seller_embed.add_field(
                    name="Order ID",
                    value=str(order.id),
                    inline=False,
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
                seller_embed.set_footer(
                    text="Use /shopadmin commands to manage this order."
                )
                await seller.send(embed=seller_embed)
            except (discord.Forbidden, discord.NotFound):
                logger.warning(
                    "Could not DM seller %s for order %s",
                    product.seller_xid,
                    order.id,
                )
