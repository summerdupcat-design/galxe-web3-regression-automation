import os
import re

import allure
from playwright.sync_api import Page, expect


FOLLOWING_SPACES_URL = os.getenv(
    "GALXE_FOLLOWING_SPACES_URL",
    "https://app.galxe.com/quest/spaces/following",
)

FOLLOWING_URL_PATTERN = re.compile(r"/quest/spaces/following/?(?:\?.*)?$")
ALL_SPACES_URL_PATTERN = re.compile(r"/quest/spaces/all/?(?:\?.*)?$")
SPACE_DETAIL_URL_PATTERN = re.compile(r"/quest/(?!spaces(?:/|$)|explore/)[^/?]+")
SPACE_CARD_SELECTOR = (
    'main a[href^="/quest/"]:not([href="/quest/spaces/all"])'
    ':not([href="/quest/spaces/following"])'
)


class FollowingSpacesPage:
    def __init__(self, page: Page):
        self.page = page

    @allure.step("打开 Following Spaces 页面")
    def open(self) -> None:
        self.page.goto(FOLLOWING_SPACES_URL, wait_until="load")
        self.page.bring_to_front()
        expect(self.page).to_have_url(FOLLOWING_URL_PATTERN, timeout=30_000)

    @allure.step("断言 Following Spaces 未登录页面加载成功")
    def assert_logged_out_state(self) -> None:
        expect(self.page).to_have_title(re.compile("My Following Spaces"))
        expect(self.page.get_by_text("Log in to Discover and Stay Updated")).to_be_visible(
            timeout=30_000
        )
        expect(self._tab("All")).to_be_visible(timeout=30_000)
        expect(self._tab("Following")).to_be_visible(timeout=30_000)
        expect(self.create_space_link()).to_be_visible(timeout=30_000)

    @allure.step("点击页面登录按钮")
    def click_login_prompt(self) -> None:
        main_login = self.page.locator("main").get_by_role(
            "button", name=re.compile(r"^Log in$", re.I)
        )
        expect(main_login).to_be_visible(timeout=30_000)
        main_login.click()

    @allure.step("断言登录弹窗可见")
    def assert_login_dialog_visible(self) -> None:
        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=30_000)
        wallet_option = dialog.get_by_text(
            re.compile(r"MetaMask|WalletConnect|Log in to Galxe", re.I)
        )
        expect(wallet_option.first).to_be_visible(timeout=30_000)

    @allure.step("点击 All tab")
    def open_all_tab(self) -> None:
        all_tab = self._tab("All")
        expect(all_tab).to_be_visible(timeout=30_000)
        all_tab.click()
        expect(self.page).to_have_url(ALL_SPACES_URL_PATTERN, timeout=30_000)

    @allure.step("获取 Create Space 入口")
    def create_space_link(self):
        return self.page.get_by_role("link", name=re.compile(r"Create Space", re.I))

    @allure.step("点击 Create Space 入口")
    def assert_create_space_link_points_to_onboard(self) -> None:
        link = self.create_space_link()
        expect(link).to_be_visible(timeout=30_000)
        href = link.get_attribute("href")
        assert href and "dashboard.galxe.com/onboard" in href

    @allure.step("获取 Following Space 卡片")
    def get_space_cards(self):
        return self.page.locator(SPACE_CARD_SELECTOR)

    @allure.step("打开第一个 Following Space 详情")
    def open_first_space_detail_or_skip(self) -> str | None:
        cards = self.get_space_cards()
        if cards.count() == 0:
            return None
        first_card = cards.first
        expect(first_card).to_be_visible(timeout=30_000)
        card_title = first_card.inner_text().split("\n")[0].strip()
        first_card.click()
        expect(self.page).to_have_url(SPACE_DETAIL_URL_PATTERN, timeout=30_000)
        return card_title

    def _tab(self, name: str):
        return self.page.get_by_role("tab", name=re.compile(rf"^{name}", re.I)).first
