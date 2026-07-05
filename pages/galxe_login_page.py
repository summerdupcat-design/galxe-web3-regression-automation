import re

import allure
from playwright.sync_api import BrowserContext, Locator, Page, TimeoutError, expect

from pages.metamask_page import MetamaskPage
from utils.config import get_base_url


class GalxeLoginPage:
    def __init__(self, page: Page):
        self.page = page

    @property
    def login_button(self):
        return self.page.get_by_role("banner").get_by_role(
            "button", name=re.compile(r"Log in|Login", re.I)
        )

    def _login_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_text(re.compile(r"Log in to Galxe", re.I))
        )

    def is_login_dialog_open(self) -> bool:
        dialog = self._login_dialog()
        return dialog.count() > 0 and dialog.first.is_visible()

    def _is_dashboard_logged_in(self) -> bool:
        if "dashboard" not in self.page.url:
            return False
        banner = self.page.get_by_role("banner")
        authenticated_actions = banner.get_by_role(
            "button", name=re.compile(r"Next Step|Save Draft|Release", re.I)
        )
        return (
            authenticated_actions.count() > 0
            and authenticated_actions.first.is_visible(timeout=3_000)
        )

    def is_logged_in(self) -> bool:
        if self.is_login_dialog_open():
            return False
        if self._is_dashboard_logged_in():
            return True
        return not self.login_button.is_visible(timeout=5_000)

    @allure.step("关闭阻塞弹窗")
    def dismiss_blocking_dialogs(self) -> None:
        for _ in range(5):
            dialogs = self.page.get_by_role("dialog")
            if dialogs.count() == 0:
                break
            close_btn = dialogs.first.get_by_role(
                "button", name=re.compile(r"Close|关闭", re.I)
            )
            if close_btn.count() and close_btn.first.is_visible():
                close_btn.first.click(force=True)
                self.page.wait_for_timeout(300)
            else:
                break

    @allure.step("确保处于未登录状态")
    def ensure_logged_out(self, context: BrowserContext) -> None:
        self.page.goto(get_base_url(), wait_until="load")
        self.page.bring_to_front()
        self.dismiss_blocking_dialogs()

        if self.login_button.is_visible(timeout=5_000):
            return

        self._logout_via_ui()
        expect(self.login_button).to_be_visible(timeout=10_000)

        context.clear_cookies()
        self.page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        self.page.reload(wait_until="load")
        self.dismiss_blocking_dialogs()

        if not self.login_button.is_visible(timeout=10_000):
            self._logout_via_ui()

        expect(self.login_button).to_be_visible(timeout=30_000)

    def _logout_via_ui(self) -> None:
        self.dismiss_blocking_dialogs()
        avatar_button = self.page.get_by_role("banner").get_by_role(
            "button", name=re.compile(r"avatar", re.I)
        )
        expect(avatar_button.first).to_be_visible(timeout=10_000)
        avatar_button.first.click()

        avatar_menu = self.page.get_by_role("menu", name=re.compile(r"avatar", re.I))
        expect(avatar_menu).to_be_visible(timeout=5_000)

        disconnect_item = avatar_menu.get_by_role(
            "menuitem", name=re.compile(r"Disconnect", re.I)
        )
        expect(disconnect_item.first).to_be_visible(timeout=5_000)
        disconnect_item.first.click(force=True)
        expect(self.login_button).to_be_visible(timeout=15_000)

    @allure.step("断言钱包对话框可见")
    def assert_wallet_dialog_visible(self) -> None:
        dialog = self._login_dialog()
        expect(dialog).to_be_visible(timeout=30_000)
        wallet_options = dialog.get_by_text(
            re.compile(
                r"MetaMask|WalletConnect|Use another Galxe account|Recent",
                re.I,
            )
        )
        expect(wallet_options.first).to_be_visible(timeout=30_000)

    @allure.step("点击登录按钮")
    def click_login_button(self) -> None:
        self.page.bring_to_front()
        if self.is_login_dialog_open():
            self.assert_wallet_dialog_visible()
            return
        if self._is_dashboard_logged_in():
            return
        login_button = self.login_button
        expect(login_button).to_be_visible(timeout=30_000)
        login_button.scroll_into_view_if_needed()
        login_button.click()
        self.assert_wallet_dialog_visible()

    @allure.step("选择MetaMask")
    def choose_metamask(self, context: BrowserContext) -> Page:
        dialog = self._login_dialog()
        expect(dialog).to_be_visible(timeout=30_000)

        use_another = dialog.get_by_text(re.compile(r"Use another Galxe account", re.I))
        if use_another.count() and use_another.first.is_visible(timeout=2_000):
            use_another.first.click()
            self.page.wait_for_timeout(500)
            dialog = self._login_dialog()

        metamask = dialog.get_by_text(re.compile(r"MetaMask", re.I))
        expect(metamask.first).to_be_visible(timeout=30_000)
        return self._click_metamask_and_get_popup(context, metamask.first)

    def _click_metamask_and_get_popup(
        self, context: BrowserContext, metamask_locator: Locator
    ) -> Page:
        existing_pages = set(context.pages)
        try:
            with context.expect_page(timeout=5_000) as popup_info:
                metamask_locator.click()
            return popup_info.value
        except TimeoutError:
            metamask_locator.click()

        for _ in range(60):
            new_pages = [
                page
                for page in context.pages
                if page not in existing_pages and "chrome-extension://" in page.url
            ]
            if new_pages:
                return new_pages[-1]
            for page in context.pages:
                if "chrome-extension://" in page.url and "notification.html" in page.url:
                    return page
            self.page.wait_for_timeout(500)

        raise TimeoutError("MetaMask popup not found")

    @allure.step("MetaMask 登录")
    def login_with_metamask(self, context: BrowserContext) -> None:
        if self.is_logged_in():
            self.assert_login_success()
            return
        metamask = MetamaskPage(context)
        metamask.ensure_unlocked()
        self.dismiss_blocking_dialogs()
        if not self.is_login_dialog_open():
            self.click_login_button()
        else:
            self.assert_wallet_dialog_visible()
        popup = self.choose_metamask(context)
        action = metamask.approve_popup(popup)
        if action == "connect":
            try:
                sign_popup = context.wait_for_event("page", timeout=5_000)
                metamask.approve_popup(sign_popup)
            except TimeoutError:
                if popup and not popup.is_closed():
                    metamask.approve_popup(popup)
        self.page.wait_for_timeout(1_000)
        self.assert_login_success()

    @allure.step("确保页面已登录")
    def ensure_logged_in(self, context: BrowserContext, url: str | None = None) -> None:
        if url:
            self.page.goto(url, wait_until="load")
            self.page.bring_to_front()
        else:
            self.page.goto(get_base_url(), wait_until="load")
            self.page.bring_to_front()
        self.dismiss_blocking_dialogs()
        if not self.is_logged_in():
            self.login_with_metamask(context)
        else:
            self.assert_login_success()

    @allure.step("断言登录成功")
    def assert_login_success(self) -> None:
        self.page.bring_to_front()
        self.dismiss_blocking_dialogs()
        if self._is_dashboard_logged_in():
            return
        avatar = self.page.get_by_role("banner").get_by_role(
            "button", name=re.compile(r"avatar", re.I)
        )
        expect(avatar.first).to_be_visible(timeout=30_000)
