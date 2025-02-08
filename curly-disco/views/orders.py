from typing import Any, Dict, List

import models
from cex import ExchangeInterface
from initdb import InitDB
from nicegui import ui
from views.slots import Slots


class OrdersView(ExchangeInterface):
    ORDERS_SCHEMA = [
        {"name": "id", "label": "ID", "field": "id", "sortable": True},
        {"name": "pair", "label": "Pair", "field": "pair", "sortable": True},
        {"name": "side", "label": "Side", "field": "side", "sortable": True},
        {"name": "type", "label": "Type", "field": "type", "sortable": True},
        {"name": "quantity", "label": "Quantity", "field": "quantity", "sortable": True},
        {"name": "current_price", "label": "Current Price", "field": "current_price", "sortable": True},
        {"name": "target_price", "label": "Target Price", "field": "target_price", "sortable": True},
        {"name": "far", "label": "Far", "field": "far", "sortable": True},
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
                        "far": round(far, 2),
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
        self.orders_table.add_slot(
            "body-cell-side",
            """<q-td key="side" :props="props">
                <q-badge :color="props.value === 'SELL' ? 'red' : 'green'">
                {{ props.value }}
                </q-badge>
                </q-td>""",
        )

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

    async def __synchronise_all_trades(self):
        notif = ui.notification(timeout=None)
        initDB = InitDB(spot=self.client)
        notif.message = "Synchronizing trades..."
        notif.spinner = True
        await initDB.init_orders_and_trades()
        notif.message = "Synchronization done."
        notif.spinner = False
        notif.dismiss()

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
        with ui.row():
            ui.button("Refresh", on_click=self.panel_trades.refresh)
            ui.button("Synchronize", color="green", on_click=self.__synchronise_all_trades)
        await self.panel_trades()
