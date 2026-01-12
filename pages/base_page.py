class BasePage:
    def __init__(self, page):
        self.page = page

    def navigate(self, url):
        self.page.goto(url)

    def get_title(self):
        return self.page.title()

    def wait_for_page_load(self):
        self.page.wait_for_load_state("networkidle")

        