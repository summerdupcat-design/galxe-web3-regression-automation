import re

from playwright.sync_api import Page, expect

from pages.explore_space_page import ExploreSpacePage
from utils.config import get_base_url


def open_homepage(page: Page):
    page.goto(get_base_url(), wait_until="networkidle")


def test_space_explore_all_should_show_all_spaces(page: Page):
    open_homepage(page)
    space_page = ExploreSpacePage(page)
    space_page.open_all_spaces()
    space_cards = space_page.get_space_cards()
    card_count = space_cards.count()
    print(f"card_count: {card_count}")
    assert card_count > 0


def test_open_first_space_detail(page: Page):
    open_homepage(page)
    space_page = ExploreSpacePage(page)
    space_page.open_all_spaces()
    space_title = space_page.open_first_space_detail()
    expect(page).to_have_title(re.compile(re.escape(space_title)))
