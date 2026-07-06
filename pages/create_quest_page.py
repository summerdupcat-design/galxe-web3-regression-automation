import os
import re
from datetime import date, timedelta
import allure
from playwright.sync_api import BrowserContext, Page, expect

from pages.galxe_login_page import GalxeLoginPage

QUEST_CREATE_URL = os.getenv(
    "QUEST_CREATE_URL",
    "https://dashboard.stg.galxe.com/quest/create?space=263",
)
QUEST_DETAIL_URL = re.compile(r"/quest/[^/]+/[^/?]+")


class CreateQuestPage:
    def __init__(self, page: Page):
        self.page = page

    @property
    def next_step_button(self):
        return self.page.get_by_role("banner").get_by_role("button", name="Next Step")

    @allure.step("打开创建Quest页面")
    def open(self, url: str = QUEST_CREATE_URL, context: BrowserContext | None = None) -> None:
        if context is not None:
            GalxeLoginPage(self.page).ensure_logged_in(context, url)
        else:
            self.page.goto(url, wait_until="load")
            self.page.bring_to_front()
        expect(self.next_step_button).to_be_visible(timeout=30_000)
    @allure.step("Quest Info: 设置Quest Info")
    def set_quest_info(self, title: str, description: str) -> None:
        self.page.get_by_placeholder("Enter quest title").fill(title)
        self.page.get_by_placeholder("Enter quest description").fill(description)
        self._fill_quest_period()

    @allure.step("Quest Info: 设置Quest Private")
    def set_quest_private(self) -> None:
        private_radio = self.page.get_by_role("radio", name="Private")
        expect(private_radio).to_be_visible(timeout=30_000)
        private_radio.click()
        expect(private_radio).to_be_checked()

    @allure.step("Reward Info: 设置Point Reward")
    def set_point_reward(self, recurrence: str = "Once") -> None:
        expect(self.page.get_by_test_id("Points")).to_be_visible(timeout=30_000)
        self.page.get_by_test_id("Points").click()
        self.page.get_by_role("button", name="Fixed Points").click()
        self.page.get_by_role("button", name=recurrence).click()
    @allure.step("Task Settings: 设置Quest Task Group")
    def set_quest_task_group(
        self,
        page_name: str,
        page_link: str,
        points: str = "10",
    ) -> None:
        expect(self.page.get_by_text("Set Up Task Group", exact=True)).to_be_visible(
            timeout=30_000
        )
        self.page.get_by_text("Set Up Task Group", exact=True).click()
        dialog = self.page.get_by_role("dialog")
        dialog.get_by_text("Visit a Page", exact=True).click()
        dialog.get_by_placeholder("Please input the Page name").fill(page_name)
        dialog.get_by_placeholder(
            "Please paste the link the users need to visit"
        ).fill(page_link)
        dialog.get_by_role("button", name="Save").click()
        expect(dialog).not_to_be_visible(timeout=20_000)
        self._set_task_group_points_reward(points)

    @allure.step("Task Settings: 禁用Participation Requirement")
    def disable_participation_requirement(self) -> None:
        participation_switch = self._participation_requirement_switch()
        if participation_switch.is_checked():
            participation_switch.click()
        expect(participation_switch).not_to_be_checked()

    @allure.step("Task Settings: 启用No Task Requirement")
    def enable_no_task_requirement(self, points: str = "10") -> None:
        self.disable_participation_requirement()

        no_task_label = self.page.get_by_text("No Task Requirement", exact=True)
        expect(no_task_label).to_be_visible(timeout=30_000)
        no_task_switch = no_task_label.locator("xpath=ancestor::div[1]").get_by_role(
            "switch"
        )
        expect(no_task_switch).to_be_enabled(timeout=30_000)
        if not no_task_switch.is_checked():
            no_task_switch.click()
        expect(no_task_switch).to_be_checked()
        self._set_points_reward_amount(points)
    @allure.step("跳转至Next Step")
    def go_to_next_step(self) -> None:
        self.next_step_button.click()

    @allure.step("保存Draft")
    def save_draft(self) -> None:
        self.page.get_by_role("button", name="Save Draft").click()
        expect(
            self.page.get_by_text("Saved Quest Successfully.", exact=True).first
        ).to_be_visible(timeout=30_000)

    @allure.step("Release Quest")
    def release(self, quest_title: str) -> str:
        release_btn = self.page.get_by_role("banner").get_by_role(
            "button", name="Release"
        )
        expect(release_btn).to_be_enabled(timeout=30_000)
        release_btn.click()

        dialog = self.page.get_by_role("dialog")
        expect(dialog).to_be_visible(timeout=30_000)

        ignore_release = dialog.get_by_role("button", name="Ignore and Release")
        if ignore_release.is_visible(timeout=5_000):
            ignore_release.click()
            dialog = self.page.get_by_role("dialog")
            expect(dialog).to_be_visible(timeout=30_000)

        expect(dialog.get_by_text("After Release")).to_be_visible(timeout=30_000)
        dialog.get_by_role("button", name="Release Now").click()

        expect(self.page).to_have_url(QUEST_DETAIL_URL, timeout=60_000)
        expect(
            self.page.get_by_text(quest_title, exact=True).first
        ).to_be_visible(timeout=30_000)
        return self.page.url
    @allure.step("Quest Info: 设置Quest Period")
    def _fill_quest_period(self) -> None:
        start = date.today()
        end = start + timedelta(days=1)

        self.page.get_by_text("Start date", exact=True).click()
        self.page.wait_for_timeout(500)

        self._pick_calendar_date(start)
        self.page.wait_for_timeout(200)
        if (end.year, end.month) != (start.year, start.month):
            self._go_to_next_month()
        self._pick_calendar_date(end)

        self.page.get_by_role("button", name="OK").click(force=True)
        self.page.wait_for_timeout(500)

    @allure.step("Quest Info: 选择日历日期")
    def _pick_calendar_date(self, target: date) -> None:
        day_str = str(target.day)
        cells = self.page.get_by_role("gridcell")
        for i in range(cells.count()):
            cell = cells.nth(i)
            if cell.get_attribute("aria-disabled") == "true":
                continue
            if cell.inner_text().strip() == day_str:
                cell.click()
                return

        raise RuntimeError(f"Calendar day not found: {target.isoformat()}")

    @allure.step("Quest Info: 跳转至下一月")
    def _go_to_next_month(self) -> None:
        next_month = self.page.get_by_role(
            "button", name=re.compile(r"Next|Go to next month", re.I)
        )
        expect(next_month.first).to_be_visible(timeout=10_000)
        next_month.first.click()
        self.page.wait_for_timeout(300)

    @allure.step("Task Settings: 获取Participation Requirement Switch")
    def _participation_requirement_switch(self):
        requirement_label = self.page.get_by_text(
            re.compile(r"Participation Requirement")
        )
        expect(requirement_label).to_be_visible(timeout=30_000)
        return requirement_label.locator("xpath=ancestor::div[1]").get_by_role(
            "switch"
        )
    @allure.step("Task Settings: 设置Quest Task Group Points Reward")
    def _set_task_group_points_reward(self, points: str) -> None:
        self._set_points_reward_amount(points)

    @allure.step("Task Settings: 设置Quest Task Group Points Reward Amount")
    def _set_points_reward_amount(self, points: str) -> None:
        points_input = (
            self.page.get_by_text("# of Point(s) Reward")
            .locator("xpath=ancestor::div[1]")
            .locator("input")
        )
        expect(points_input).to_be_visible(timeout=30_000)
        points_input.fill(points)
        points_input.press("Tab")
