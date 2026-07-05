from playwright.sync_api import Page, expect
from pages.space_page import SpacePage
from utils.config import get_base_url


def open_homepage(page: Page):
    page.goto(get_base_url(), wait_until="networkidle")


def test_space_explore_all_should_show_all_spaces(page: Page):
    open_homepage(page)
    space_page = SpacePage(page)
    space_page.open_all_spaces()
    space_cards = space_page.get_space_cards()
    card_count = space_cards.count()
    print(f"card_count: {card_count}")
    assert card_count > 0


def test_open_first_space_detail(page: Page):
    open_homepage(page)
    space_page = SpacePage(page)
    space_page.open_all_spaces()
    space_title = space_page.open_first_space_detail()
    expect(page.locator("main").get_by_text(space_title, exact=True).first).to_be_visible()

def test_user_should_be_prompted_to_connect_wallet_when_clicking_follow_button(
    logged_out_page: Page,
):
    page = logged_out_page
    space_page = SpacePage(page)
    space_page.open_all_spaces()
    space_page.open_first_space_detail()
    space_page.click_space_follow_button()
    space_page.assert_connect_wallet_dialog_is_visible()
    
def test_user_should_follow_space_successfully(logged_in_page):
    page = logged_in_page
    space_page = SpacePage(page)
    space_page.open_all_spaces()
    space_page.open_first_space_detail()
    space_page.ensure_not_following()
    space_page.click_space_follow_button()
    space_page.assert_user_follow_success()  

def test_user_unfollow_space_successfully(logged_in_page):
    page = logged_in_page
    space_page = SpacePage(page)
    space_page.open_all_spaces()
    space_page.open_first_space_detail()
    space_page.ensure_following()
    space_page.click_space_unfollow_button()
    space_page.confirm_unfollow_space()
    space_page.assert_user_unfollow_success()