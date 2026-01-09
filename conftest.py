import pytest
from playwright.sync_api import sync_playwright
import os
from pytest_html import extras
import base64
from datetime import datetime

# ---------------------------------------------------------------------------------
# Fixture: browser_context
# Purpose: Launches a new browser context for each test, provides a page object,
#          and ensures cleanup after test completion.
# ---------------------------------------------------------------------------------
@pytest.fixture(scope="function")
def browser_context(request):
    with sync_playwright() as p:
        # Launch Chromium browser; change headless=True for headless mode
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Attach page object to the test node for later use (e.g., screenshots)
        request.node.page = page

        yield page  # This will be passed to your test as 'browser_context'

        # Close context and browser after test finishes
        context.close()
        browser.close()


# ---------------------------------------------------------------------------------
# Hook: pytest_runtest_makereport
# Purpose: Triggered after each test, checks if test failed.
#          Takes a timestamped screenshot if test fails and embeds it in the HTML report.
# ---------------------------------------------------------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Run the normal pytest reporting first
    outcome = yield
    rep = outcome.get_result()

    # Only act on actual test execution ('call') and failures
    if rep.when == "call" and rep.failed:
        page = getattr(item, "page", None)
        if page:
            # Create timestamp for unique screenshot filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshots_dir = "reports/screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)

            # Screenshot filename: testname_timestamp.png
            screenshot_file = f"{screenshots_dir}/{item.name}_{timestamp}.png"
            page.screenshot(path=screenshot_file)

            # Encode screenshot as Base64 and attach to HTML report
            with open(screenshot_file, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode("utf-8")
            
            # ✅ Updated for latest pytest-html: use 'extras' instead of deprecated 'extra'
            rep.extras = getattr(rep, "extras", [])
            rep.extras.append(extras.image(f"data:image/png;base64,{encoded_string}"))

            print(f"\n[Screenshot saved] {screenshot_file}")


# ---------------------------------------------------------------------------------
# Hook: pytest_configure
# Purpose: Add corporate-ready metadata to HTML report and dynamically set
#          timestamped report filename if none is provided (works with VS Code Run button)
# ---------------------------------------------------------------------------------
def pytest_configure(config):
    # Only add metadata if pytest-html plugin is active
    if config.pluginmanager.hasplugin("html"):
        # Add metadata
        config._metadata = getattr(config, "_metadata", {})
        config._metadata.update({
            "Project": "Playwright Automation Framework",
            "Test Environment": "Staging",
            "Browser": "Chromium",
            "Headless": "False"
        })

        # Automatically generate timestamped HTML report if no path provided
        if not hasattr(config.option, "htmlpath") or not config.option.htmlpath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("reports", exist_ok=True)
            config.option.htmlpath = f"reports/report_{timestamp}.html"