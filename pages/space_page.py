import re
from playwright.sync_api import Page, expect
import allure
SPACE_LIST_URL = re.compile(r"/quest/spaces/all")
SPACE_DETAIL_URL = re.compile(r"/quest/(?!explore/|spaces(?:/|$))[^/?]+/?$")
SPACE_CARD = 'a[href^="/quest/"]:not([href="/quest/explore/all"]):not([href="/quest/spaces"]):not([href="/quest/spaces/all"])'

class SpacePage:
    def __init__(self, page: Page):
        self.page = page

    @allure.step("打开所有Spaces页面")
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

    @allure.step("获取Space Cards")
    def get_space_cards(self, timeout: int = 30_000):
        space_cards = self.page.get_by_role("tabpanel").locator(SPACE_CARD)
        expect(space_cards.first).to_be_visible(timeout=timeout)
        return space_cards
    
    @allure.step("打开第一个Space详情页面")
    def open_first_space_detail(self):
        space_cards = self.get_space_cards()
        card_count = space_cards.count()
        for index in range(min(card_count, 5)):
            card = space_cards.nth(index)
            space_title = card.inner_text().split("\n")[0].strip()
            card.click()
            self.page.wait_for_url(SPACE_DETAIL_URL)
            self.page.wait_for_load_state("load")
            if self._is_space_detail_ready():
                return space_title
            if index < min(card_count, 5) - 1:
                self.page.go_back()
                self.page.wait_for_url(SPACE_LIST_URL)
                space_cards = self.get_space_cards()
        raise RuntimeError("No accessible space detail page found")

    def _is_space_detail_ready(self) -> bool:
        if self.page.get_by_text("Oops, Page Not Found").is_visible(timeout=2_000):
            return False
        follow = self._follow_button()
        following = self._following_button()
        return (follow.count() and follow.first.is_visible()) or (
            following.count() and following.first.is_visible()
        )

    @allure.step("获取Follow按钮")
    def _follow_button(self):
        return self.page.get_by_role(
            "button", name=re.compile(r"^\+?\s*Follow$", re.I)
        )

    @allure.step("获取Following按钮")
    def _following_button(self):
        return self.page.get_by_role(
            "button", name=re.compile(r"^Following$", re.I)
        )

    @allure.step("确保未Following")
    def ensure_not_following(self) -> None:
        if self._follow_button().count() and self._follow_button().first.is_visible():
            return
        self.click_space_unfollow_button()
        self.confirm_unfollow_space()
        expect(self._follow_button().first).to_be_visible(timeout=30_000)

    @allure.step("确保Following")
    def ensure_following(self) -> None:
        if self._following_button().count() and self._following_button().first.is_visible():
            return
        self.click_space_follow_button()
        self.assert_user_follow_success()

    @allure.step("点击Follow按钮")
    def click_space_follow_button(self):
        follow_button = self._follow_button()
        expect(follow_button.first).to_be_visible(timeout=30_000)
        follow_button.first.scroll_into_view_if_needed()
        follow_button.first.click()

    @allure.step("点击Unfollow按钮")
    def click_space_unfollow_button(self):
        unfollow_button = self._following_button()
        expect(unfollow_button.first).to_be_visible(timeout=30_000)
        unfollow_button.first.scroll_into_view_if_needed()
        unfollow_button.first.click()

    @allure.step("二次确认Unfollow")
    def confirm_unfollow_space(self):
        confirm_dialog = self.page.get_by_role("dialog")
        expect(confirm_dialog).to_be_visible(timeout=30_000)
        confirm_button = confirm_dialog.get_by_role(
            "button", name=re.compile(r"^Confirm$|^Unfollow$|^确认$", re.I)
        )
        expect(confirm_button.first).to_be_visible(timeout=30_000)
        confirm_button.first.click()

    @allure.step("断言Follow成功")
    def assert_user_follow_success(self):
        expect(self._following_button().first).to_be_visible(timeout=30_000)

    @allure.step("断言Unfollow成功")
    def assert_user_unfollow_success(self):
        expect(self._follow_button().first).to_be_visible(timeout=30_000)
    
    @allure.step("断言Connect Wallet对话框可见")
    def assert_connect_wallet_dialog_is_visible(self):
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=30_000)
        expect(dialog.get_by_text("MetaMask", exact=True).first).to_be_visible(
            timeout=30_000
        )