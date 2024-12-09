import os

import initdb
import models
import watcher
from db import DB
from nicegui import app, ui
from views.slots import Slots

app.on_startup(DB.init())
app.on_disconnect(DB.close())
_watcher = watcher.Watcher(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])
_initdb = initdb.InitDB(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])

NUMBER_OF_ITEMS = 20


@ui.refreshable
async def panel_asset():
    with ui.row():
        with ui.card().props("flat bordered"):
            ui.label("Total value")
            ui.label("1000$")
        with ui.card().props("flat bordered"):
            ui.label("Total gains")
            ui.label("1000$")
        with ui.card().props("flat bordered"):
            ui.label("Liquidity locked")
            ui.label("1000$")
        with ui.card().props("flat bordered"):
            ui.label("Liquidity available")
            ui.label("1000$")

    ui.label("Current assets")
    with ui.table(
        columns=models.Assets.nicegui_repr(),
        rows=await _watcher.get_upto_date_asset(),
        row_key="id",
        pagination=NUMBER_OF_ITEMS,
    ) as home_table:
        home_table.add_slot("loading", "True")
        home_table.add_slot("body-cell-gains", Slots.slot_red_green("gains", "$"))
        home_table.add_slot("body-cell-gains_percentage", Slots.slot_red_green("gains_percentage", "%"))
        # home_table.add_slot("body-cell-updated_at", slot_timestamp("updated_at"))


@ui.refreshable
async def panel_open_orders():
    order_columns = [
        {"name": "Pair", "label": "pair", "field": "pair", "sortable": True},
        {"name": "Quantity", "label": "quantity", "field": "quantity", "sortable": True},
        {"name": "Current price", "label": "current", "field": "current_price", "sortable": True},
        {"name": "Target price", "label": "target", "field": "target_price", "sortable": True},
        {"name": "Far", "label": "far", "field": "far", "sortable": True},
    ]
    open_orders = await _watcher.get_opened_buy_orders()
    ui.table(columns=order_columns, rows=open_orders, pagination=NUMBER_OF_ITEMS, row_key="pair")


@ui.refreshable
async def panel_trades():
    trades = await models.Trades.all().values()
    trades.sort(key=lambda x: x["closed_at"], reverse=True)
    with ui.table(
        columns=models.Trades.nicegui_repr(), rows=trades, pagination=NUMBER_OF_ITEMS, row_key="id"
    ) as trades_table:
        trades_table.add_slot("body-cell-gains", Slots.slot_red_green("gains", "$"))
        trades_table.add_slot("body-cell-gains_percentage", Slots.slot_red_green("gains_percentage", "%"))


async def manual_update_assets():
    ui.notify("Updating assets...")
    await _initdb.init_assets()
    ui.notify("Assets updated!")


async def manual_update_trades():
    ui.notify("Updating trades...")
    await _initdb.init_orders_and_trades()
    ui.notify("Trades updated!")


async def manual_update_market():
    ui.notify("Updating market...")
    await _initdb.init_market()
    ui.notify("Market updated!")


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
            ui.button("Refresh", on_click=panel_asset.refresh)
            await panel_asset()

        with ui.tab_panel("Open orders"):
            ui.button("Refresh", on_click=panel_open_orders.refresh)
            await panel_open_orders()

        with ui.tab_panel("Trades").classes("w-full"):
            ui.button("Refresh", on_click=panel_trades.refresh)
            await panel_trades()

        with ui.tab_panel("Controls"):
            ui.label("Controls")
            ui.button("Resync assets", on_click=lambda: manual_update_assets())
            ui.button("Resync trades", on_click=lambda: manual_update_trades())
            ui.button("Resync market", on_click=lambda: manual_update_market())


ui.dark_mode(value=True)
ui.run(reload=False)
