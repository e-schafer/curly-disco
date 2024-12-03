import os

import models
import watcher
from db import DB
from nicegui import app, ui

app.on_startup(DB.init())
app.on_disconnect(DB.close())
_watcher = watcher.Watcher(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])


@ui.page("/", title="Curly Disco", response_timeout=20.0)
async def index():
    with ui.header().classes(replace="row items-center"):
        # ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props("flat color=white")
        with ui.tabs() as tabs:
            ui.tab("Home")
            ui.tab("Open orders")
            ui.tab("Trades")
            ui.tab("Controls")

    # with ui.left_drawer().classes("bg-blue-100") as left_drawer:
    #     ui.label("Side menu")

    with ui.tab_panels(tabs, value="Home"):
        with ui.tab_panel("Home"):
            ui.label("Home")
            columns = models.Assets.nicegui_repr()
            ui.table(
                columns=columns,
                rows=await models.Assets.all().values(),
                pagination=50,
            )

        with ui.tab_panel("Open orders"):
            order_columns = [
                {"name": "Pair", "label": "pair", "field": "pair"},
                {"name": "Quantity", "label": "quantity", "field": "quantity"},
                {"name": "Current price", "label": "current", "field": "current_price"},
                {"name": "Target price", "label": "target", "field": "target_price"},
                {"name": "Far", "label": "far", "field": "far"},
            ]
            open_orders = await _watcher.buy_orders()
            ui.table(columns=order_columns, rows=open_orders, pagination=50, row_key="pair")
        with ui.tab_panel("Trades").classes("w-full"):
            ui.label("Trades")
            trades = await models.Trades.all().values()
            trades.sort(key=lambda x: x["closed_at"], reverse=True)
            ui.table(columns=models.Trades.nicegui_repr(), rows=trades, pagination=50, row_key="id")

        with ui.tab_panel("Controls"):
            ui.label("Controls")


ui.dark_mode(value=True)
ui.run()
