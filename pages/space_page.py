import re
from playwright.sync_api import Page, expect

SPACE_LIST_URL = re.compile(r"/quest/spaces/all")
SPACE_DETAIL_URL = re.compile(r"/quest/(?!explore/|spaces(?:/|$))[^/?]+/?$")
SPACE_CARD = 'a[href^="/quest/"]:not([href="/quest/explore/all"]):not([href="/quest/spaces"]):not([href="/quest/spaces/all"])'

class SpacePage:
    def __init__(self, page: Page):
        self.page = page

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

    def get_space_cards(self, timeout: int = 30_000):
        space_cards = self.page.get_by_role("tabpanel").locator(SPACE_CARD)
        expect(space_cards.first).to_be_visible(timeout=timeout)
        return space_cards
    
    def open_first_space_detail(self):
        space_cards = self.get_space_cards()
        first_space = space_cards.first
        space_title = first_space.inner_text().split("\n")[0].strip()
        first_space.click()
        self.page.wait_for_url(SPACE_DETAIL_URL)
        return space_title

    