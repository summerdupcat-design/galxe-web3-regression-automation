import re
from playwright.sync_api import Page, expect

SPACE_LIST_URL = re.compile(r"/quest/spaces/all")
SPACE_DETAIL_URL = re.compile(r"/quest/(?!explore/|spaces(?:/|$))[^/?]+/?$")
SPACE_CARD = 'a[href^="/quest/"]:not([href="/quest/explore/all"]):not([href="/quest/spaces"]):not([href="/quest/spaces/all"])'

class SpacePage:
    def __init__(self, page: Page):
        self.page = page

    def open_all_spaces(self):
        nav = self.page.get_by_role("navigation")
        explore_btn = nav.get_by_role("button", name="Explore")
        expect(explore_btn).to_be_visible()
        explore_btn.hover()
        all_spaces = self.page.get_by_role("link", name="All", exact=True).nth(1)
        expect(all_spaces).to_be_visible()
        all_spaces.click()
        self.page.wait_for_url(SPACE_LIST_URL)
        self.get_space_cards()

    def get_space_cards(self, timeout: int = 30_000):
        space_cards = self.page.get_by_role("tabpanel").locator(SPACE_CARD)
        expect(space_cards.first).to_be_visible(timeout=timeout)
        return space_cards
    
    def open_first_space_detail(self):
        space_cards = self.get_space_cards()
        first_space = space_cards.first
        space_title = first_space.inner_text().split("\n")[0].strip()
        first_space.click()
        self.page.wait_for_url(SPACE_DETAIL_URL)
        return space_title

    def _follow_button(self):
        return self.page.get_by_role(
            "button", name=re.compile(r"^\+\s*Follow$", re.I)
        )

    def _following_button(self):
        return self.page.get_by_role(
            "button", name=re.compile(r"^Following$", re.I)
        )

    def ensure_following(self) -> None:
        if self._following_button().count() and self._following_button().first.is_visible():
            return
        self.click_space_follow_button()
        self.assert_user_follow_success()

    def click_space_follow_button(self):
        follow_button = self._follow_button()
        expect(follow_button.first).to_be_visible(timeout=30_000)
        follow_button.first.scroll_into_view_if_needed()
        follow_button.first.click()

    def click_space_unfollow_button(self):
        unfollow_button = self._following_button()
        expect(unfollow_button.first).to_be_visible(timeout=30_000)
        unfollow_button.first.scroll_into_view_if_needed()
        unfollow_button.first.click()

    def confirm_unfollow_space(self):
        confirm_dialog = self.page.get_by_role("dialog")
        expect(confirm_dialog).to_be_visible(timeout=30_000)
        confirm_button = confirm_dialog.get_by_role(
            "button", name=re.compile(r"^Confirm$|^Unfollow$|^确认$", re.I)
        )
        expect(confirm_button.first).to_be_visible(timeout=30_000)
        confirm_button.first.click()

    def assert_user_follow_success(self):
        expect(self._following_button().first).to_be_visible(timeout=30_000)

    def assert_user_unfollow_success(self):
        expect(self._follow_button().first).to_be_visible(timeout=30_000)
    def assert_connect_wallet_dialog_is_visible(self):
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=30_000)
        expect(dialog.get_by_text("MetaMask", exact=True).first).to_be_visible(
            timeout=30_000
        )