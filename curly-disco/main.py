import os
import traceback
from hashlib import sha256
from typing import Optional

import initdb
from db import DB
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, ui
from nicegui.elements.input import Input
from starlette.middleware.base import BaseHTTPMiddleware
from views.asset import AssetView
from views.command import CommandView
from views.market import MarketView
from views.orders import OrdersView, TradesView
from views.settings import SettingsView
from watcher import Watcher

VERSION = "0.4.0"
AUTHENTICATION = os.environ["AUTHENTICATION_HASH"]
BINANCE_API_KEY = os.environ["BINANCE_API_KEY"]
BINANCE_API_SECRET = os.environ["BINANCE_API_SECRET"]
SKIP_INIT_HISTORIC = True if os.getenv("SKIP_INIT_HISTORIC", "").lower() == "true" else False
SKIP_INIT_ENTRIES = True if os.getenv("SKIP_INIT_ENTRIES", "").lower() == "true" else False
DISABLE_WATCHER = True if os.getenv("DISABLE_WATCHER", "").lower() == "true" else False

print("SKIP_INIT_HISTORIC", SKIP_INIT_HISTORIC)
print("SKIP_INIT_ENTRIE", SKIP_INIT_ENTRIES)
print("DISABLE_WATCHER", DISABLE_WATCHER)

UNRESTRICTED_PAGE_ROUTES = {"/login"}
_initdb = initdb.InitDB(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_watcher = Watcher(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_market = MarketView(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_commands = CommandView(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_orders = OrdersView(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_trades = TradesView(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_assets = AssetView(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
_settings = SettingsView()


@app.add_middleware
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


@app.on_startup
async def startup():
    await DB.init()
    await _initdb.init_settings()
    await _initdb.init_market()
    await _initdb.init_assets()
    if not SKIP_INIT_HISTORIC:
        await _initdb.init_orders_and_trades()
    if not DISABLE_WATCHER:
        _watcher.start_watch()
        _watcher.loop_entries()  # type: ignore
        _watcher.loop_exit()  # type: ignore
    if not SKIP_INIT_ENTRIES:
        await _watcher.strat_loop_compute_exit()
        await _watcher.strat_loop_compute_entry()


@app.on_exception
async def error(error: Exception):
    ui.notify(
        "Website Exception: \n" f"{traceback.format_exception(error)} \n",
        multi_line=True,
        classes="multi-line-notification",
    )


@app.on_shutdown
async def shutdown():
    _watcher.stop_watch()
    app.storage.user.clear()
    await DB.close()
    print("Robot stopped")


@ui.page("/", title="Robot", response_timeout=20.0)
async def index():
    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to("/login")

    with ui.header().classes(replace="row items-center"):
        with ui.tabs() as tabs:
            ui.tab("Home")
            ui.tab("Assets")
            ui.tab("Orders")
            ui.tab("Settings")
        with ui.row().classes("items-center absolute-right"):
            ui.label(f"pomato {VERSION}")
            ui.button(on_click=logout, icon="logout").props("outline round")
    with ui.tab_panels(tabs, value="Assets", keep_alive=False):
        with ui.tab_panel("Home"):
            ui.markdown(
                """
                # Welcome to Curly Disco
                This is a simple trading bot that uses the Binance API to trade.
                """
            )
            await _market.render()
        with ui.tab_panel("Assets"):
            await _assets.render()
            await _trades.render()
        with ui.tab_panel("Orders"):
            await _orders.render()
            await _commands.render()
        with ui.tab_panel("Settings"):
            await _settings.render()


@ui.page("/login", title="Login")
def login() -> Optional[RedirectResponse]:
    def try_login() -> None:  # local function to avoid passing username and password as arguments
        if AUTHENTICATION == sha256(f"{username.value}:{password.value}".encode("utf-8")).hexdigest():
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


ui.dark_mode().enable()
ui.run(reload=False, storage_secret="THIS_NEEDS_TO_BE_CHANGED")
