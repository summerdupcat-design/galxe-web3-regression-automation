import allure
import pytest
from playwright.sync_api import BrowserContext, Page, expect

from pages.following_spaces_page import FOLLOWING_SPACES_URL, FollowingSpacesPage
from pages.galxe_login_page import GalxeLoginPage


@allure.epic("Galxe")
@allure.feature("Spaces")
@allure.story("Following Spaces")
def test_following_spaces_logged_out_should_show_login_prompt(guest_page: Page):
    following_page = FollowingSpacesPage(guest_page)

    following_page.open()
    following_page.assert_logged_out_state()


@allure.epic("Galxe")
@allure.feature("Spaces")
@allure.story("Following Spaces")
def test_following_spaces_login_prompt_should_open_login_dialog(guest_page: Page):
    following_page = FollowingSpacesPage(guest_page)

    following_page.open()
    following_page.click_login_prompt()
    following_page.assert_login_dialog_visible()


@allure.epic("Galxe")
@allure.feature("Spaces")
@allure.story("Following Spaces")
def test_following_spaces_all_tab_should_navigate_to_all_spaces(guest_page: Page):
    following_page = FollowingSpacesPage(guest_page)

    following_page.open()
    following_page.open_all_tab()


@allure.epic("Galxe")
@allure.feature("Spaces")
@allure.story("Following Spaces")
def test_following_spaces_create_space_should_open_onboard(guest_page: Page):
    following_page = FollowingSpacesPage(guest_page)

    following_page.open()
    following_page.assert_create_space_link_points_to_onboard()


@allure.epic("Galxe")
@allure.feature("Spaces")
@allure.story("Following Spaces")
def test_logged_in_following_spaces_should_open_first_space_detail(
    page: Page,
    context: BrowserContext,
):
    GalxeLoginPage(page).ensure_logged_in(context, url=FOLLOWING_SPACES_URL)
    following_page = FollowingSpacesPage(page)

    following_page.open()
    card_title = following_page.open_first_space_detail_or_skip()
    if not card_title:
        pytest.skip("当前测试账号没有 Following Space，跳过列表详情冒烟。")

    expect(page.locator("main").get_by_text(card_title, exact=True).first).to_be_visible(
        timeout=30_000
    )
