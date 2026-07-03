import re

from playwright.sync_api import Page, expect


class GalxeLoginPage:
    def __init__(self, page: Page):
        self.page = page

    def click_login_button(self) -> None:
        self.page.bring_to_front()
        login_button = self.page.get_by_role("banner").get_by_role(
            "button", name=re.compile(r"Log in|Login", re.I)
        )
        expect(login_button).to_be_visible(timeout=30_000)
        login_button.scroll_into_view_if_needed()
        login_button.click()
        expect(self.page.get_by_role("dialog")).to_be_visible(timeout=30_000)

    def choose_metamask(self) -> None:
        metamask = self.page.get_by_text("MetaMask", exact=True)
        expect(metamask).to_be_visible(timeout=30_000)
        metamask.click()
