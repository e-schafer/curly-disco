import asyncio

import models
import watcher
from binance.error import ClientError
from cex import ExchangeInterface
from initdb import InitDB
from nicegui import ui
from watcher import Watcher


class CommandView(ExchangeInterface):
    PANEL_NAME = "Commands"

    def __init__(self, api_key, api_secret):
        super().__init__(api_key, api_secret)

    async def __confirm_action(self, funct, message="Are you sure?"):
        with ui.dialog() as dialog, ui.card():
            ui.label(message)
            with ui.row(align_items="center"):
                ui.button("Yes", on_click=lambda: dialog.submit(True))
                ui.button("No", on_click=lambda: dialog.submit(False))
        result = await dialog
        if result:
            funct()

    def __cancel_all_orders(self):
        orders = self.client.get_open_orders()
        for order in orders:
            try:
                self.client.cancel_order(symbol=order["symbol"], orderId=order["orderId"])
            except ClientError as e:
                ui.notify(f"Error cancelling order: {e}", level="warning", color="red")
        ui.notify(f"{len(orders)} orders cancelled", level="warning")

    def __cancel_all_buy(self):
        orders = self.client.get_open_orders()
        orders = list(filter(lambda x: x["side"] == "BUY", orders))
        for order in orders:
            try:
                self.client.cancel_order(symbol=order["symbol"], orderId=order["orderId"])
            except ClientError as e:
                ui.notify(f"Error cancelling order: {e}", level="warning", color="red")
        ui.notify(f"{len(orders)} orders cancelled", level="warning")

    def __put_order(self, symbol: str, side: str, type: str, quantity: float, price: float):
        print(f"put order: pair={symbol}, side={side}, type={type}, quantity={quantity}, price={price}")
        try:
            order = {
                "symbol": symbol,
                "side": side,
                "type": type,
                "quantity": quantity,
            }
            if type == "LIMIT":
                order["timeInForce"] = "GTC"
                order["price"] = price
            response = self.client.new_order(**order)
            ui.notify(f"Order placed for {response['symbol']}", level="info", color="green")
        except Exception as e:
            print(f"Error putting order: {e}")
            ui.notify(f"Error putting order: {e}", level="error", color="red")

    def __validate_number(self, quantity):
        try:
            float(quantity)
            return True
        except ValueError:
            return False

    async def __sync_market(self):
        notif = ui.notification(timeout=None)
        notif.message = "Synchronizing market..."
        notif.spinner = True
        await InitDB(spot=self.client).init_market()
        notif.spinner = False
        notif.message = "Synchronization done."
        notif.dismiss()

    async def __sync_buy_strategy(self):
        notif = ui.notification(timeout=None)
        notif.message = "Synchronizing market..."
        notif.spinner = True
        await Watcher(spot=self.client).strat_loop_compute_entry()
        notif.spinner = False
        notif.message = "Synchronization done."
        notif.dismiss()

    async def render(self):
        # add market buy order select from model.Markets
        with ui.row():
            select_pair = ui.select(
                label="Pair",
                options=await models.Market.all().values_list("pair", flat=True),
                with_input=True,
                new_value_mode="add-unique",
            )
            select_side = ui.select(label="Side", options=["BUY", "SELL"], with_input=True)
            select_type = ui.select(label="Type", options=["MARKET", "LIMIT"], with_input=True)
            input_qty = ui.input(
                label="Quantity",
                placeholder="0.0",
                validation={"Not a number": lambda x: self.__validate_number(x)},
            ).props("clearable")
            input_price = ui.input(
                label="Price",
                placeholder="0.0",
                validation={"Not a number": lambda x: self.__validate_number(x)},
            ).props("clearable")
            ui.button("Put Order", icon="add").on_click(
                lambda: self.__put_order(
                    symbol=select_pair.value,
                    side=select_side.value,
                    type=select_type.value,
                    quantity=input_qty.value,
                    price=input_price.value,
                )
            )
        # cancel all orders
        with ui.row():
            ui.button("Cancel all orders", color="red").on_click(
                lambda: self.__confirm_action(self.__cancel_all_orders, "Cancel all orders.\nAre you sure?")
            )
            ui.button("Cancel all buy orders", color="red").on_click(
                lambda: self.__confirm_action(self.__cancel_all_buy, "Cancel all buy orders.\nAre you sure?")
            )
            ui.button("Sync tradable pairs", color="green").on_click(self.__sync_market)
            ui.button("Restart buy strategy", color="gold").on_click(self.__sync_buy_strategy)
