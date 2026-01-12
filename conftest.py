import pytest
from playwright.sync_api import sync_playwright
import os
from pytest_html import extras
import base64
from datetime import datetime
from config.config import Config

# ---------------------------------------------------------------------------------
# Fixture: page
# Purpose: Launch browser based on config, create isolated context & page per test
# ---------------------------------------------------------------------------------
@pytest.fixture(scope="function")
def page(request):
    with sync_playwright() as p:

        # -------- Browser selection from Config --------
        if Config.BROWSER == "chromium":
            browser = p.chromium.launch(headless=Config.HEADLESS)
        elif Config.BROWSER == "firefox":
            browser = p.firefox.launch(headless=Config.HEADLESS)
        else:
            browser = p.webkit.launch(headless=Config.HEADLESS)

        # -------- Context setup --------
        context = browser.new_context()
        context.set_default_timeout(Config.DEFAULT_TIMEOUT)
        context.set_default_navigation_timeout(Config.DEFAULT_TIMEOUT)

        # (Optional but powerful) Enable tracing
        context.tracing.start(screenshots=True, snapshots=True)

        page = context.new_page()

        # Attach page & context to test node (used in reporting hooks)
        request.node.page = page
        request.node.context = context

        yield page

        # -------- Teardown --------
        context.close()
        browser.close()


# ---------------------------------------------------------------------------------
# Hook: pytest_runtest_makereport
# Purpose: On failure → screenshot + trace + embed in HTML report
# ---------------------------------------------------------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.when == "call" and rep.failed:
        page = getattr(item, "page", None)
        context = getattr(item, "context", None)

        # Worker-safe folder (for future parallel runs)
        worker = os.environ.get("PYTEST_XDIST_WORKER", "main")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshots_dir = f"reports/screenshots/{worker}"
        traces_dir = f"reports/traces/{worker}"

        os.makedirs(screenshots_dir, exist_ok=True)
        os.makedirs(traces_dir, exist_ok=True)

        if page:
            screenshot_file = f"{screenshots_dir}/{item.name}_{timestamp}.png"
            page.screenshot(path=screenshot_file)

            with open(screenshot_file, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode("utf-8")

            rep.extras = getattr(rep, "extras", [])
            rep.extras.append(
                extras.image(f"data:image/png;base64,{encoded_string}")
            )

            print(f"\n[Screenshot saved] {screenshot_file}")

        # Save Playwright trace (HUGE debugging help)
        if context:
            trace_file = f"{traces_dir}/{item.name}_{timestamp}.zip"
            context.tracing.stop(path=trace_file)
            print(f"[Trace saved] {trace_file}")


# ---------------------------------------------------------------------------------
# Hook: pytest_configure
# Purpose: Add metadata + auto-generate timestamped HTML report
# ---------------------------------------------------------------------------------
def pytest_configure(config):
    if config.pluginmanager.hasplugin("html"):
        config._metadata = getattr(config, "_metadata", {})
        config._metadata.update({
            "Project": "Playwright Automation Framework",
            "Base URL": Config.BASE_URL,
            "Browser": Config.BROWSER,
            "Headless": str(Config.HEADLESS),
            "Timeout (ms)": str(Config.DEFAULT_TIMEOUT)
        })

        if not hasattr(config.option, "htmlpath") or not config.option.htmlpath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("reports", exist_ok=True)
            config.option.htmlpath = f"reports/report_{timestamp}.html"