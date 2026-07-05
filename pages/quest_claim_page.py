import os
import re
from dataclasses import dataclass
import allure
from playwright.sync_api import BrowserContext, Page, expect

from utils.gravity_chain import extract_tx_hash

QUEST_CLAIM_URL = os.getenv(
    "QUEST_CLAIM_URL",
    "https://app.stg.galxe.com/quest/Summertest/GCTeNU4K2P",
)
VISIT_CREDENTIAL_TEST_ID = "cred-item-VISIT_LINK"
VISIT_PAGE_WAIT_MS = 8_000
EXPLORER_LINK_PATTERN = re.compile(r"mainnet-explorer\.gravity\.xyz|View on", re.I)


@dataclass
class ClaimResult:
    tx_hash: str | None = None
    explorer_url: str | None = None


class QuestClaimPage:
    def __init__(self, page: Page):
        self.page = page

    @property
    @allure.step("获取Claim按钮")
    def claim_button(self):
        return self.page.get_by_role("button", name=re.compile(r"Claim \d+ Points"))

    @property
    @allure.step("获取Visit Credential按钮")
    def visit_credential(self):
        return self.page.get_by_test_id(VISIT_CREDENTIAL_TEST_ID)

    @allure.step("打开Quest Claim页面")
    def open(self, url: str = QUEST_CLAIM_URL, *, require_credential: bool = True) -> None:
        self.page.goto(url, wait_until="load")
        self.page.bring_to_front()
        self.page.set_viewport_size({"width": 1440, "height": 900})
        self._dismiss_blocking_dialogs()
        if require_credential:
            expect(self.visit_credential).to_be_visible(timeout=30_000)
        else:
            expect(self.claim_button.first).to_be_visible(timeout=30_000)

    @allure.step("完成Visit Credential")
    def complete_visit_credential(self, context: BrowserContext) -> None:
        cred = self.visit_credential
        cred.scroll_into_view_if_needed()

        if self._is_credential_completed(cred):
            return

        self._expand_credential(cred)
        verify_button = cred.locator("button").filter(
            has=self.page.get_by_test_id("verify-button")
        )

        with context.expect_page(timeout=15_000) as visit_page_info:
            self._click_element(verify_button.first)
        visit_page = visit_page_info.value
        visit_page.wait_for_load_state("load")
        visit_page.wait_for_timeout(VISIT_PAGE_WAIT_MS)
        visit_page.close()

        self.page.bring_to_front()
        self.page.wait_for_timeout(1_000)
        self._click_element(verify_button.first)
        expect(cred.locator(".bg-success")).to_be_visible(timeout=30_000)

    @allure.step("Claim Reward")
    def claim_reward(self, context: BrowserContext):
        self._dismiss_blocking_dialogs()
        claim_btn = self.claim_button
        expect(claim_btn.first).to_be_visible(timeout=30_000)
        expect(claim_btn.first).to_be_enabled(timeout=30_000)
        claim_btn.first.scroll_into_view_if_needed()

        popup = None
        try:
            with context.expect_page(timeout=10_000) as popup_info:
                claim_btn.first.click()
            popup = popup_info.value
        except Exception:
            claim_btn.first.click()

        if popup and "chrome-extension://" in popup.url:
            popup.bring_to_front()
            return popup

        self.page.bring_to_front()
        return None

    @allure.step("等待Claim成功")
    def wait_for_claim_success(self) -> ClaimResult:
        expect(
            self.page.get_by_text(
                re.compile(
                    r"Claimed|Already claimed|Transaction submitted successfully",
                    re.I,
                )
            ).first
        ).to_be_visible(timeout=60_000)

        explorer_link = self.page.locator(
            'a[href*="mainnet-explorer.gravity.xyz/tx/"]'
        )
        expect(explorer_link.first).to_be_visible(timeout=30_000)
        explorer_url = explorer_link.first.get_attribute("href")
        if not explorer_url:
            raise AssertionError("Claim explorer URL not found after successful claim")

        return ClaimResult(
            tx_hash=extract_tx_hash(explorer_url),
            explorer_url=explorer_url,
        )

    @allure.step("Complete Claim")
    def complete_claim(self, context: BrowserContext, metamask) -> ClaimResult:
        popup = self.claim_reward(context)
        if popup:
            metamask.approve_popup(popup)

        self.page.bring_to_front()
        self._dismiss_blocking_dialogs()
        return self.wait_for_claim_success()

    @allure.step("断言Claim成功")
    def assert_reward_claimed(self) -> None:
        self.wait_for_claim_success()

    @allure.step("断言Credential完成")
    def _is_credential_completed(self, cred) -> bool:
        return cred.locator(".bg-success").count() > 0

    @allure.step("展开Credential")
    def _expand_credential(self, cred) -> None:
        header = cred.locator("[aria-expanded]").first
        if header.get_attribute("aria-expanded") == "false":
            header.click()
            self.page.wait_for_timeout(500)

    @allure.step("点击元素")
    def _click_element(self, locator) -> None:
        handle = locator.element_handle()
        if handle is None:
            locator.click(force=True)
            return
        self.page.evaluate("el => el.click()", handle)

    @allure.step("关闭Blocking Dialogs")
    def _dismiss_blocking_dialogs(self) -> None:
        for _ in range(3):
            dialog = self.page.get_by_role("dialog")
            if dialog.count() == 0 or not dialog.first.is_visible():
                return

            close_button = dialog.get_by_role(
                "button", name=re.compile(r"Close", re.I)
            )
            if close_button.count() and close_button.first.is_visible():
                close_button.first.click()
                self.page.wait_for_timeout(500)
                continue
            return
