from pages.base_page import BasePage
from utils.env_reader import load_env_properties

class GitHubLoginPage(BasePage):

    def __init__(self, page):
        super().__init__(page)
        self.creds = load_env_properties()

        self.username = page.locator("#login_field")
        self.password = page.locator("#password")
        self.sign_in_btn = page.get_by_role("link", name="Sign in")

    def login(self):
        self.username.fill(self.creds["GITHUB_USERNAME"])
        self.password.fill(self.creds["GITHUB_PASSWORD"])
        self.sign_in_btn.click()