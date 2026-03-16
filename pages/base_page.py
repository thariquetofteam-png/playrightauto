from playwright.sync_api import Page, expect
import os
import time

class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str):
        self.page.goto(url, timeout=60000)

    def wait_for_page_load(self):
        self.page.wait_for_load_state("networkidle")

    def click(self, locator: str):
        self.page.locator(locator).click()

    def fill(self, locator: str, value: str):
        self.page.locator(locator).fill(value)

    def get_text(self, locator: str) -> str:
        return self.page.locator(locator).inner_text()

    def wait_for_element(self, locator: str):
        self.page.locator(locator).wait_for(state="visible")

    def take_screenshot(self, name: str):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = f"screenshots/{name}_{timestamp}.png"
        os.makedirs("screenshots", exist_ok=True)
        self.page.screenshot(path=path, full_page=True)
