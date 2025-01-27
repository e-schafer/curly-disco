from datetime import datetime
from typing import Literal

import models
from cex import ExchangeInterface
from nicegui import ui

from .slots import Slots


class AssetView(ExchangeInterface):
    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)
        self.asset_table = None

    async def init_assets(self):
        ui.notify("Synchronisation started", level="ongoing")
        await models.Assets.all().delete()
        pairs = list(
            map(
                lambda y: f"{y['asset']}USDT",
                filter(
                    lambda x: x["asset"] not in ("USDT", "BNB"),
                    self.client.account(omitZeroBalances="true").get("balances"),
                ),
            )
        )
        for pair in pairs:
            print(f"Fetching open trades for {pair}")
            orders = list(filter(lambda x: x["status"] == "FILLED", self.client.get_orders(symbol=pair)))
            orders.sort(key=lambda x: x["time"], reverse=True)
            token_quantity: float = 0.0
            quote_quantity: float = 0.0
            opened_at: datetime = datetime(1970, 1, 1)
            for order in orders:
                if order["side"] == "SELL":
                    break
                token_quantity += float(order.get("origQty", 0))
                quote_quantity += float(order.get("cummulativeQuoteQty", 0))
                opened_at = datetime.fromtimestamp(order["time"] / 1000)

            current_unit_price = float((self.client.ticker_price(pair))["price"])
            await models.Assets.create(
                id=pair,
                token_quantity=token_quantity,
                quote_quantity=quote_quantity,
                buy_unit_price=quote_quantity / token_quantity,
                market_value=token_quantity * current_unit_price,
                market_unit_price=current_unit_price,
                gains=token_quantity * current_unit_price - quote_quantity,
                gains_percentage=((token_quantity * current_unit_price) / quote_quantity - 1) * 100,
                opened_at=opened_at,
            )
        ui.notify("Synchronisation done", level="positive")

    @ui.refreshable
    async def asset_view(self) -> None:
        await self.update_assets_gains()
        assets = await models.Assets.all().values()
        liquidity = await self.get_liquidity()
        with ui.row():
            with ui.card().props("flat bordered"):
                ui.label("Total gains")
                ui.label(f"{round(liquidity['total_gains'],2)}$")
            with ui.card().props("flat bordered"):
                ui.label("Open gains")
                open_gains = round(liquidity["market_value"] - liquidity["bought"], 2)
                gains_label = ui.label(f"{open_gains}$")
                if open_gains > 0:
                    gains_label.classes("text-positive")
                else:
                    gains_label.classes("text-negative")
            with ui.card().props("flat bordered"):
                ui.label("Market value")
                ui.label(f"{round(liquidity['market_value'],2)}$")
            with ui.card().props("flat bordered"):
                ui.label("Liquidity engaged")
                ui.label(f"{round(liquidity['bought'],2)}$")
            with ui.card().props("flat bordered"):
                ui.label("Liquidity locked")
                ui.label(f"{round(liquidity['locked'],2)}$")
            with ui.card().props("flat bordered"):
                ui.label("Liquidity available")
                ui.label(f"{round(liquidity['free'],2)}$")
        ui.label("Current assets")
        self.asset_table = ui.table(
            columns=models.Assets.nicegui_repr(),
            rows=assets,
            row_key="id",
            pagination=super().NUMBER_OF_ITEMS,
            selection="multiple",
        )
        self.asset_table.add_slot("loading", "True")
        self.asset_table.add_slot("body-cell-gains", Slots.slot_red_green("gains", "$"))
        self.asset_table.add_slot("body-cell-gains_percentage", Slots.slot_red_green("gains_percentage", "%"))
        # home_table.add_slot("body-cell-updated_at", slot_timestamp("updated_at"))
        return None

    async def __sell_selected_assets(self, type=Literal["MARKET", "LIMIT"]):
        selected_assets = self.asset_table.selected
        for asset in selected_assets:
            payload = {
                "symbol": asset["id"],
                "side": "SELL",
                "type": type,
                "quantity": asset["token_quantity"],
            }
            if type == "LIMIT":
                payload["price"] = asset["buy_unit_price"]
                payload["timeInForce"] = "GTC"
            try:
                self.client.new_order(**payload)
                ui.notify(f"{type} sell order for {asset['id']} send", level="info")
            except Exception as e:
                ui.notify(f"Error selling asset: {e}", level="warning", color="red")
        self.asset_view.refresh()

    async def render(self):
        with ui.row(align_items="stretch"):
            ui.button("Refresh", on_click=self.asset_view.refresh)
            ui.button("Synchronize", on_click=self.init_assets, color="green")
            ui.button("Sell market", on_click=lambda: self.__sell_selected_assets(type="MARKET"), color="red")
            ui.button("Sell break even", on_click=lambda: self.__sell_selected_assets(type="LIMIT"), color="red")
        await self.asset_view()
