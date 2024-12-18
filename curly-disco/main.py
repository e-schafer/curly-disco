import asyncio
import os
from pprint import pp

import initdb
import models
import watcher
from db import DB
from nicegui import app, events, ui
from views.slots import Slots

# VERSION = importlib.metadata.version("curly-disco")
VERSION = "0.1.0"
NUMBER_OF_ITEMS = 20


_initdb = initdb.InitDB(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])
_watcher = watcher.Watcher(api_key=os.environ["API_KEY_WRITE"], api_secret=os.environ["API_SECRET_WRITE"])


@app.on_startup
async def startup():
    await DB.init()
    # await _initdb.init_settings()
    # await _initdb.init_market()
    # await _initdb.init_assets()
    # await _initdb.init_orders_and_trades()
    # _watcher.loop_entries()  # type: ignore
    # _watcher.loop_exit()  # type: ignore


@app.on_exception
async def error(error: Exception):
    ui.notify(str(error))


@app.on_shutdown
async def shutdown():
    await DB.close()


@ui.refreshable
async def panel_home() -> None:
    liquidity = await _watcher.get_liquidity()
    with ui.row():
        with ui.card().props("flat bordered"):
            ui.label("Total gains")
            ui.label(f"{liquidity['total_gains']}$")
        with ui.card().props("flat bordered"):
            ui.label("Market value")
            ui.label(f"{liquidity['market_value']}$")
        with ui.card().props("flat bordered"):
            ui.label("Liquidity engaged")
            ui.label(f"{liquidity['bought']}$")
        with ui.card().props("flat bordered"):
            ui.label("Liquidity locked")
            ui.label(f"{liquidity['locked']}$")
        with ui.card().props("flat bordered"):
            ui.label("Liquidity available")
            ui.label(f"{liquidity['free']}$")
    ui.label("Current assets")
    await _watcher.update_assets_gains()
    assets = await models.Assets.all().values()
    with ui.table(
        columns=models.Assets.nicegui_repr(),
        rows=assets,
        row_key="id",
        pagination=NUMBER_OF_ITEMS,
    ) as home_table:
        home_table.add_slot("loading", "True")
        home_table.add_slot("body-cell-gains", Slots.slot_red_green("gains", "$"))
        home_table.add_slot("body-cell-gains_percentage", Slots.slot_red_green("gains_percentage", "%"))
        # home_table.add_slot("body-cell-updated_at", slot_timestamp("updated_at"))


@ui.refreshable
async def panel_open_orders() -> None:
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
async def panel_trades() -> None:
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


async def manual_update_market():
    ui.notify("Updating market...")
    await _initdb.init_market()
    ui.notify("Market updated!")


async def update_settings(e: events.GenericEventArguments):
    ui.notify("Updating settings...")
    pp(e.args)
    if setting := await models.Settings.get_or_none(key=e.args["key"]):
        setting.value = e.args["value"]
        await setting.save()
        ui.notify("Settings updated!")


@ui.page("/", title="Curly Disco", response_timeout=20.0)
async def index():
    with ui.header().classes(replace="row items-center"):
        with ui.tabs() as tabs:
            ui.tab("Home")
            ui.tab("Open orders")
            ui.tab("Settings")
            # ui.tab("Controls")
        ui.label(f"Curly Disco {VERSION}")
    with ui.tab_panels(tabs, value="Home"):
        with ui.tab_panel("Home"):
            ui.button("Refresh", on_click=panel_home.refresh)
            await panel_home()
            ui.button("Refresh", on_click=panel_trades.refresh)
            await panel_trades()
        with ui.tab_panel("Open orders"):
            ui.button("Refresh", on_click=panel_open_orders.refresh)
            await panel_open_orders()
        with ui.tab_panel("Settings"):
            with ui.table(
                rows=await models.Settings.all().values(), columns=models.Settings.nicegui_repr()
            ) as settings_table:
                settings_table.add_slot(
                    "body-cell-value",
                    """
                    <q-td key="value" :props="props">
                    {{ props.row.value }}
                    <q-popup-edit v-model="props.row.value" v-slot="scope"  @update:model-value="() => $parent.$emit('update', props.row)">
                    <q-input v-model.number="scope.value" type="number"  dense autofocus counter @keyup.enter="scope.set" />
                    </q-popup-edit>
                    </q-td>""",
                )
                settings_table.on("update", update_settings)

        with ui.tab_panel("Controls"):
            ui.label("Controls")
            ui.button("Resync assets", on_click=lambda: manual_update_assets())
            # ui.button("Resync trades", on_click=lambda: manual_update_trades())
            ui.button("Resync market", on_click=lambda: manual_update_market())


ui.dark_mode(value=True)
ui.run(reload=False)
