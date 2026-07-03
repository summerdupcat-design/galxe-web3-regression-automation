import re 
from playwright.sync_api import BrowserContext, Page, expect


class GalxeLoginPage:
    def __init__(self, page: Page):
        self.page = page

    def assert_wallet_dialog_visible(self) -> None:
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=30_000)
        expect(dialog.get_by_text("MetaMask")).to_be_visible(timeout=30_000)

    def click_login_button(self) -> None:
        self.page.bring_to_front()
        login_button = self.page.get_by_role("banner").get_by_role(
            "button", name=re.compile(r"Log in|Login", re.I)
        )
        expect(login_button).to_be_visible(timeout=30_000)
        login_button.scroll_into_view_if_needed()
        login_button.click()
        self.assert_wallet_dialog_visible()

    def choose_metamask(self, context: BrowserContext) -> Page:
        metamask = self.page.get_by_text("MetaMask", exact=True)
        expect(metamask).to_be_visible(timeout=30_000)
        with context.expect_page() as popup_info:
            metamask.click()
        return popup_info.value

    def assert_login_success(self) -> None:
        self.page.bring_to_front()
        login_button = self.page.get_by_role("banner").get_by_role(
            "button", name=re.compile(r"Log in|Login", re.I)
        )
        expect(login_button).not_to_be_visible(timeout=30_000)