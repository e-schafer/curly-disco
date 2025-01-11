import os
import traceback
from hashlib import sha256
from typing import Optional

import initdb
import models
import watcher
from db import DB
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, events, ui
from nicegui.elements.input import Input
from starlette.middleware.base import BaseHTTPMiddleware
from views.slots import Slots

VERSION = "0.2.1"
NUMBER_OF_ITEMS = 20
AUTHENICATION = os.environ["AUTHENTICATION_HASH"]
BINANCE_API_KEY = os.environ["BINANCE_API_KEY"]
BINANCE_API_SECRET = os.environ["BINANCE_API_SECRET"]
SKIP_INIT_HISTORIC = True if os.environ["SKIP_INIT_HISTORIC"].lower() == "true" else False
SKIP_INIT_ENTRIES = True if os.environ["SKIP_INIT_ENTRIES"].lower() == "true" else False

print("SKIP_INIT_HISTORIC", SKIP_INIT_HISTORIC)
print("SKIP_INIT_ENTRIE", SKIP_INIT_ENTRIES)

UNRESTRICTED_PAGE_ROUTES = {"/login"}
_initdb = initdb.InitDB(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_watcher = watcher.Watcher(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)


class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get("authenticated", False):
            if not request.url.path.startswith("/_nicegui") and request.url.path not in UNRESTRICTED_PAGE_ROUTES:
                app.storage.user["referrer_path"] = request.url.path  # remember where the user wanted to go
                return RedirectResponse("/login")
        return await call_next(request)


app.add_middleware(AuthMiddleware)


@app.on_startup
async def startup():
    await DB.init()
    await _initdb.init_settings()
    await _initdb.init_market()
    await _initdb.init_assets()
    if not SKIP_INIT_HISTORIC:
        await _initdb.init_orders_and_trades()
    if not SKIP_INIT_ENTRIES:
        await _watcher.strat_loop_compute_entry()
    _watcher.loop_entries()  # type: ignore
    _watcher.loop_exit()  # type: ignore


@app.on_exception
async def error(error: Exception):
    ui.notify(
        "Website Exception: \n" f"{traceback.format_exception(error)} \n",
        multi_line=True,
        classes="multi-line-notification",
    )


@app.on_shutdown
async def shutdown():
    await DB.close()


@ui.refreshable
async def panel_home() -> None:
    liquidity = await _watcher.get_liquidity()
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
    return None


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
    return None


@ui.refreshable
async def panel_trades() -> None:
    trades = await models.Trades.all().values()
    trades.sort(key=lambda x: x["closed_at"], reverse=True)
    with ui.table(
        columns=models.Trades.nicegui_repr(), rows=trades, pagination=NUMBER_OF_ITEMS, row_key="id"
    ) as trades_table:
        trades_table.add_slot("body-cell-gains", Slots.slot_red_green("gains", "$"))
        trades_table.add_slot("body-cell-gains_percentage", Slots.slot_red_green("gains_percentage", "%"))
    return None


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
    if setting := await models.Settings.get_or_none(key=e.args["key"]):
        setting.value = e.args["value"]
        await setting.save()
        ui.notify("Settings updated!")


@ui.page("/", title="Curly Disco", response_timeout=20.0)
async def index():
    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to("/login")

    with ui.header().classes(replace="row items-center"):
        with ui.tabs() as tabs:
            ui.tab("Home")
            ui.tab("Open orders")
            ui.tab("Settings")
            # ui.tab("Controls")
        with ui.row().classes("items-center absolute-right"):
            ui.label(f"pomato {VERSION}")
            ui.button(on_click=logout, icon="logout").props("outline round")
    with ui.tab_panels(tabs, value="Home"):
        with ui.tab_panel("Home"):
            ui.button("Refresh", on_click=panel_home.refresh)
            await panel_home()  # type: ignore
            ui.button("Refresh", on_click=panel_trades.refresh)
            await panel_trades()  # type: ignore
        with ui.tab_panel("Open orders"):
            ui.button("Refresh", on_click=panel_open_orders.refresh)
            await panel_open_orders()  # type: ignore
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


@ui.page("/login")
def login() -> Optional[RedirectResponse]:
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        if AUTHENICATION == sha256(f"{username.value}:{password.value}".encode("utf-8")).hexdigest():
            app.storage.user.update({"username": username.value, "authenticated": True})
            ui.navigate.to(app.storage.user.get("referrer_path", "/"))  # go back to where the user wanted to go
        else:
            ui.notify("Wrong username or password", color="negative")

    if app.storage.user.get("authenticated", False):
        return RedirectResponse("/")
    with ui.card().classes("absolute-center"):
        username: Input = ui.input("Username").on("keydown.enter", try_login)
        password = ui.input("Password", password=True, password_toggle_button=True).on("keydown.enter", try_login)
        ui.button("Log in", on_click=try_login)
    return None


ui.dark_mode(value=True)
ui.run(reload=False, storage_secret="THIS_NEEDS_TO_BE_CHANGED")
