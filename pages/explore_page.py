import re
from playwright.sync_api import Page, expect

QUEST_DETAIL_URL = re.compile(r"/quest/(?!explore/)[^/]+/[^/?]+")
class ExplorePage:
    def __init__(self, page: Page):
        self.page = page


    def open_all_quests(self):
        nav = self.page.get_by_role("navigation")
        explore_btn = nav.get_by_role("button", name="Explore")
        expect(explore_btn).to_be_visible()
        explore_btn.hover()
        all_quests = self.page.get_by_role("link", name="All", exact=True).first
        expect(all_quests).to_be_visible()
        all_quests.click()
        self.page.wait_for_url(re.compile(r"/quest/explore/all"))

    def get_quest_cards(self):
        quest_cards = self.page.locator('a[href*="refer=explore_all"]')
        return quest_cards
    
    def open_first_quest_detail(self):
        first_quest_card = self.get_quest_cards().first
        card_title = first_quest_card.locator('div.line-clamp-2.text-base.font-bold').inner_text()
        print(f"card_title: {card_title}")
        first_quest_card.click()
        self.page.wait_for_url(QUEST_DETAIL_URL)
        return card_title