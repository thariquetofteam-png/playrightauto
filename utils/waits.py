from playwright.sync_api import expect

class Waits:
    @staticmethod
    def visible(locator):
        expect(locator).to_be_visible()

    @staticmethod
    def enabled(locator):
        expect(locator).to_be_enabled()

    @staticmethod
    def has_text(locator, text):
        expect(locator).to_have_text(text)