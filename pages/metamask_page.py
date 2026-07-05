import os
import re
import subprocess
import sys
import time
from enum import Enum
import allure
from playwright.sync_api import BrowserContext, Page, expect

METAMASK_EXTENSION_ID = "nkbihfbeogaeaoehlefnkodbefgpgknn"
METAMASK_HOME_URL = f"chrome-extension://{METAMASK_EXTENSION_ID}/home.html"


class WalletState(str, Enum):
    LOGGED_IN = "logged_in"       # 已有账号，已登录
    LOCKED = "locked"             # 已有账号，未登录
    NEED_CREATE = "need_create"   # 无账号，需创建


class MetamaskPage:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.page: Page | None = None

    # 1. 访问 MetaMask
    @allure.step("访问MetaMask")
    def visit(self) -> Page:
        page = self.context.new_page()
        try:
            page.goto(f"{METAMASK_HOME_URL}#/", wait_until="domcontentloaded", timeout=60_000)
        except Exception as error:
            if "ERR_ABORTED" not in str(error):
                raise
        self._wait_for_settled(page)
        self.page = page
        self._wait_until_ready()
        self.recover_if_error()
        return page

    @allure.step("恢复MetaMask错误")
    def recover_if_error(self) -> bool:
        page = self._require_page()
        if not self._is_error_page():
            return False

        reset_button = page.get_by_role(
            "button", name=re.compile(r"重设 MetaMask 状态|Reset MetaMask")
        )
        if reset_button.count() and reset_button.first.is_visible():
            page.once("dialog", lambda dialog: dialog.accept())
            reset_button.first.click()
            page.wait_for_timeout(5_000)
            self._wait_for_settled(page)
            return True

        raise RuntimeError(
            "MetaMask 数据库已损坏（通常是导入过程中被中断）。"
            "请关闭所有 Chrome 窗口后执行: rm -rf profiles/metamask，然后重新运行。"
        )
    @allure.step("断言MetaMask错误页面")
    def _is_error_page(self) -> bool:
        page = self._require_page()
        return page.get_by_text(
            re.compile(r"MetaMask 遇到了一个错误|无法访问数据库")
        ).count() > 0

    # 2. 状态判断
    @allure.step("获取MetaMask状态")
    def get_state(self) -> WalletState:
        if self.page is None:
            raise RuntimeError("请先调用 visit() 访问 MetaMask")

        if self._is_error_page():
            raise RuntimeError(
                "MetaMask 处于错误页。请执行: rm -rf profiles/metamask 后重新初始化。"
            )

        if self._is_logged_in():
            return WalletState.LOGGED_IN
        if self._is_locked():
            return WalletState.LOCKED
        if self._need_create():
            return WalletState.NEED_CREATE
        raise RuntimeError(f"无法识别 MetaMask 状态: {self.page.url}")

    # 3. 登录账号（已有账号，输入密码解锁）
    @allure.step("登录账号")
    def login(self, password: str) -> None:
        page = self._require_page()
        password_input = page.locator('input[type="password"]')
        expect(password_input).to_be_visible(timeout=30_000)
        password_input.click()
        password_input.fill("")
        password_input.press_sequentially(password, delay=100)

        unlock_button = page.get_by_role("button", name=re.compile(r"^登录$|^Unlock$"))
        expect(unlock_button.first).to_be_enabled(timeout=30_000)
        unlock_button.first.click()
        self._dismiss_onboarding_prompts()
        expect(page.get_by_test_id("account-menu-icon")).to_be_visible(timeout=60_000)
        self._wait_until_ready()

    # 4. 创建账号（无账号，导入助记词并设置密码）
    @allure.step("导入钱包助记词，创建账号")
    def create(self, mnemonic: str, password: str) -> None:
        page = self._require_page()
        page.get_by_role("button", name="导入现有钱包").click()

        srp_button = page.get_by_role("button", name=re.compile(r"使用私钥助记词"))
        expect(srp_button.first).to_be_visible(timeout=30_000)
        srp_button.first.click()

        self._fill_mnemonic(mnemonic)

        confirm = page.get_by_test_id("import-srp-confirm")
        if confirm.is_disabled():
            raise ValueError(
                "助记词无效，MetaMask 未接受。请确认 METAMASK_MNEMONIC 是合法的 BIP39 12/24 词。"
            )
        confirm.click()
        self._set_password(password)
        self._finish_onboarding()

    # 5. 初始化钱包：访问 → 判断状态 → 登录或创建
    @allure.step("初始化钱包")
    def init_wallet(self, mnemonic: str, password: str) -> WalletState:
        self.visit()
        state = self.get_state()

        if state is WalletState.LOGGED_IN:
            return state
        if state is WalletState.LOCKED:
            self.login(password)
            return WalletState.LOGGED_IN
        self.create(mnemonic, password)
        return WalletState.LOGGED_IN

    @allure.step("获取MetaMask页面")
    def _require_page(self) -> Page:
        if self.page is None:
            raise RuntimeError("请先调用 visit() 访问 MetaMask")
        return self.page

    @allure.step("等待MetaMask页面加载完成")
    def _wait_until_ready(self, timeout: int = 60_000) -> None:
        page = self._require_page()
        spinner = page.locator(".loading-spinner")
        if spinner.count():
            spinner.wait_for(state="hidden", timeout=timeout)

    @allure.step("等待MetaMask页面 settled")
    def _wait_for_settled(self, page: Page, timeout: int = 60_000) -> None:
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            url = page.url
            if "#/onboarding" in url or "#/unlock" in url:
                break
            if page.locator('input[type="password"]').count() > 0:
                break
            account_menu = page.get_by_test_id("account-menu-icon")
            if account_menu.count() > 0 and account_menu.first.is_visible():
                break
            import_button = page.get_by_role("button", name="导入现有钱包")
            if import_button.count() > 0 and import_button.first.is_visible():
                break
            page.wait_for_timeout(200)
        else:
            raise TimeoutError(f"MetaMask 页面未就绪: {page.url}")
        spinner = page.locator(".loading-spinner")
        if spinner.count():
            spinner.wait_for(state="hidden", timeout=timeout)

    @allure.step("断言MetaMask页面已登录")
    def _is_logged_in(self) -> bool:
        page = self._require_page()
        if "#/onboarding" in page.url or "#/unlock" in page.url:
            return False
        account_menu = page.get_by_test_id("account-menu-icon")
        return account_menu.count() > 0 and account_menu.first.is_visible()

    @allure.step("断言MetaMask页面已锁定")
    def _is_locked(self) -> bool:
        page = self._require_page()
        if "#/unlock" in page.url:
            return True
        unlock_button = page.get_by_role("button", name=re.compile(r"^登录$|^Unlock$"))
        password_input = page.locator('input[type="password"]')
        return (
            unlock_button.count() > 0
            and unlock_button.first.is_visible()
            and password_input.count() == 1
        )

    @allure.step("断言MetaMask页面需创建账号")
    def _need_create(self) -> bool:
        page = self._require_page()
        import_button = page.get_by_role("button", name="导入现有钱包")
        return import_button.count() > 0 and import_button.first.is_visible()

    @allure.step("填充助记词")
    def _fill_mnemonic(self, mnemonic: str) -> None:
        page = self._require_page()
        mnemonic = " ".join(mnemonic.strip().split())

        paste_button = page.get_by_test_id("srp-input-import__paste-button")
        expect(paste_button).to_be_visible(timeout=30_000)
        paste_button.click()

        seed_input = page.locator(".srp-input-import__initial-input")
        expect(seed_input).to_be_visible(timeout=30_000)
        seed_input.click()
        self._paste_text(mnemonic)
        expect(page.get_by_test_id("import-srp-confirm")).to_be_enabled(timeout=30_000)

    @allure.step("设置密码")
    def _set_password(self, password: str) -> None:
        page = self._require_page()
        pwd_inputs = page.locator('input[type="password"]')
        expect(pwd_inputs.first).to_be_visible(timeout=30_000)
        pwd_inputs.nth(0).fill(password)
        pwd_inputs.nth(0).press("Tab")
        if pwd_inputs.count() > 1:
            pwd_inputs.nth(1).fill(password)
            pwd_inputs.nth(1).press("Tab")

        terms = page.get_by_text(re.compile(r"我已阅读|I have read"))
        if terms.count():
            terms.first.click()
        else:
            checkbox = page.locator("#create-password-terms")
            if checkbox.count():
                checkbox.check(force=True)

        submit = page.get_by_role(
            "button",
            name=re.compile(
                r"Import my wallet|导入我的钱包|创建密码|Create password|Complete|完成|Continue|继续"
            ),
        )
        expect(submit.first).to_be_enabled(timeout=30_000)
        submit.first.click()
    @allure.step("完成 onboarding")
    def _finish_onboarding(self) -> None:
        self._dismiss_onboarding_prompts()
        expect(self._require_page().get_by_test_id("account-menu-icon")).to_be_visible(
            timeout=60_000
        )
    @allure.step("关闭 onboarding 提示")
    def _dismiss_onboarding_prompts(self, timeout: int = 90) -> None:
        page = self._require_page()
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if self._is_error_page():
                raise RuntimeError(
                    "MetaMask 报错。请执行: rm -rf profiles/metamask 后重试。"
                )
            if self._is_logged_in():
                return

            clicked = False
            for pattern in (
                r"以后再说|Not now|稍后再说|No thanks|No, thanks|"
                r"知道了|Got it|全部完成|Done|下一步|Next|Skip|跳过",
            ):
                button = page.get_by_role("button", name=re.compile(pattern, re.I))
                if button.count() and button.first.is_visible() and button.first.is_enabled():
                    button.first.click()
                    page.wait_for_timeout(800)
                    clicked = True
                    break

            if not clicked:
                page.wait_for_timeout(500)

    @allure.step("粘贴文本")
    def _paste_text(self, text: str) -> None:
        page = self._require_page()
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            page.keyboard.press("Meta+v")
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode(), check=True)
            page.keyboard.press("Control+v")
        else:
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(),
                    check=True,
                )
            except FileNotFoundError:
                subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text.encode(),
                    check=True,
                )
            page.keyboard.press("Control+v")

    @allure.step("确保钱包解锁")
    def ensure_unlocked(self, password: str | None = None) -> None:
        password = password or os.getenv("METAMASK_PASSWORD", "")
        need_close = self.page is None or self.page.is_closed()
        if need_close:
            self.visit()
        elif self.get_state() == WalletState.LOCKED:
            self.login(password)
            return
        else:
            return

        if self.get_state() == WalletState.LOCKED:
            self.login(password)
        if need_close and self.page and not self.page.is_closed():
            self.page.close()
            self.page = None

    @allure.step("确保钱包解锁")
    def _unlock_if_needed(self, page: Page, password: str) -> bool:
        password_input = page.locator('input[type="password"]')
        if password_input.count() == 0 or not password_input.first.is_visible():
            return False
        if not password:
            raise RuntimeError(
                "MetaMask 已锁定，请在 .env 中设置 METAMASK_PASSWORD"
            )
        page.bring_to_front()
        password_input.first.click()
        password_input.first.fill("")
        password_input.first.press_sequentially(password, delay=100)
        unlock_button = page.get_by_role("button", name=re.compile(r"^登录$|^Unlock$"))
        expect(unlock_button.first).to_be_enabled(timeout=30_000)
        unlock_button.first.click()
        page.wait_for_load_state("domcontentloaded")
        return True

    @allure.step("连接到网站")
    def connect_to_site(self, popup: Page) -> None:
        connect_button = popup.get_by_role("button", name=re.compile(r"^连接$|^Connect$"))
        expect(connect_button.first).to_be_visible(timeout=30_000)
        connect_button.first.click()

    @allure.step("签名消息")
    def sign_message(self, popup: Page) -> None:
        sign_button = popup.get_by_role(
            "button", name=re.compile(r"^确认$|^Confirm$|^签名$|^Sign$")
        )
        expect(sign_button.first).to_be_visible(timeout=30_000)
        sign_button.first.click()

    def _enabled_button(self, popup: Page, *locators):
        for locator in locators:
            count = locator.count()
            for i in range(count):
                button = locator.nth(i)
                if button.is_visible() and button.is_enabled():
                    return button
        return None

    def _click_connect(self, popup: Page) -> bool:
        button = self._enabled_button(
            popup,
            popup.locator('[data-testid="page-container-footer-next"]'),
            popup.get_by_role("button", name=re.compile(r"^连接$|^Connect$")),
        )
        if button is None:
            return False
        button.click()
        return True

    def _click_sign(self, popup: Page) -> bool:
        button = self._enabled_button(
            popup,
            popup.locator('[data-testid="confirm-footer-button"]'),
            popup.get_by_role("button", name=re.compile(r"^确认$|^Confirm$|^签名$|^Sign$")),
        )
        if button is None:
            return False
        button.click()
        return True

    @allure.step("批准弹窗")
    def approve_popup(self, popup: Page, password: str | None = None) -> str:
        password = password or os.getenv("METAMASK_PASSWORD", "")
        popup.bring_to_front()
        popup.wait_for_load_state("domcontentloaded")
        if self._unlock_if_needed(popup, password):
            popup.wait_for_timeout(1_000)

        for _ in range(60):
            if self._click_connect(popup):
                popup.wait_for_timeout(1_000)
                if self._click_sign(popup):
                    return "sign"
                return "connect"
            if self._click_sign(popup):
                return "sign"
            popup.wait_for_timeout(500)

        raise TimeoutError("MetaMask connect/sign button not found or not enabled")
