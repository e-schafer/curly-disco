from typing import Any, Dict, List

import models
from cex import ExchangeInterface
from nicegui import ui
from views.slots import Slots


class OrdersView(ExchangeInterface):
    ORDERS_SCHEMA = [
        {"name": "ID", "label": "id", "field": "id", "sortable": True},
        {"name": "Pair", "label": "pair", "field": "pair", "sortable": True},
        {"name": "Side", "label": "side", "field": "side", "sortable": True},
        {"name": "Type", "label": "type", "field": "type", "sortable": True},
        {"name": "Quantity", "label": "quantity", "field": "quantity", "sortable": True},
        {"name": "Current price", "label": "current", "field": "current_price", "sortable": True},
        {"name": "Target price", "label": "target", "field": "target_price", "sortable": True},
        {"name": "Far", "label": "far", "field": "far", "sortable": True},
    ]

    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)
        self.orders_table = ui.table(
            columns=self.ORDERS_SCHEMA, rows=[], pagination=super().NUMBER_OF_ITEMS, row_key="pair"
        )

    async def __get_open_orders(self):
        orders = self.client.get_open_orders()
        opened_orders = []
        if orders:
            prices = await self.pairs_to_prices([x["symbol"] for x in orders])
            for order in orders:
                target_price = float(order["price"])
                current_price = prices[order["symbol"]]
                far = ((float(prices[order["symbol"]]) / target_price) - 1) * 100 if target_price else -99.0
                opened_orders.append(
                    {
                        "id": order["orderId"],
                        "pair": order["symbol"],
                        "side": order["side"],
                        "type": order["type"],
                        "quantity": order["origQty"],
                        "target_price": format(target_price, "g"),
                        "current_price": current_price,
                        "far": format(round(far, 2), "g"),
                    }
                )

        return opened_orders

    @ui.refreshable
    async def panel_open_orders(self):
        open_orders = await self.__get_open_orders()
        self.orders_table = ui.table(
            columns=self.ORDERS_SCHEMA,
            rows=open_orders,
            pagination=super().NUMBER_OF_ITEMS,
            row_key="id",
            selection="multiple",
        )
        self.orders_table.add_slot("body-cell-far", Slots.slot_red_green("far", "%"))
        # self.orders_table.add_slot(
        #     "body-cell-side",
        #     Slots.slot_red_green("side", ".", condition="""props.value === "BUY" ? "green" : "red" """),
        # )

    def __remove_selected_orders(self):
        selected_orders = self.orders_table.selected
        for order in selected_orders:
            try:
                self.client.cancel_order(symbol=order["pair"], orderId=order["id"])
            except Exception as e:
                ui.notify(f"Error cancelling order: {e}", level="warning", color="red")
        ui.notify("orders cancelled", level="info")
        self.panel_open_orders.refresh()

    async def render(self):
        with ui.row():
            ui.button("Refresh", on_click=self.panel_open_orders.refresh)
            ui.button("Delete selected orders", on_click=self.__remove_selected_orders, color="red")

        await self.panel_open_orders()


class TradesView(ExchangeInterface):
    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)

    @ui.refreshable
    async def panel_trades(self) -> None:
        trades: List[Dict[str, Any]] = await models.Trades.all().values()
        trades.sort(key=lambda x: x["closed_at"], reverse=True)
        with ui.table(
            columns=models.Trades.nicegui_repr(), rows=trades, pagination=super().NUMBER_OF_ITEMS, row_key="id"
        ) as trades_table:
            trades_table.add_slot("body-cell-gains", Slots.slot_red_green("gains", "$"))
            trades_table.add_slot("body-cell-gains_percentage", Slots.slot_red_green("gains_percentage", "%"))
        return None

    async def render(self):
        ui.button("Refresh", on_click=self.panel_trades.refresh)
        await self.panel_trades()
