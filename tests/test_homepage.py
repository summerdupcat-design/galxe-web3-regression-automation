from playwright.sync_api import Page, expect
import re
from utils.config import get_base_url

def open_homepage(page: Page):
    page.goto(get_base_url())

def assert_homepage_loaded(page: Page):
    expect(page).to_have_title(re.compile("Galxe"))
    nav = page.get_by_role("navigation")
    expect(nav.get_by_role("button", name="Explore")).to_be_visible()

def test_open_galxe_homepage(page: Page):
    open_homepage(page)
    assert_homepage_loaded(page)

