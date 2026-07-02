from playwright.sync_api import Page, expect
import re
from utils.config import get_base_url
from pages.explore_quest_page import ExploreQuestPage

QUEST_DETAIL_URL = re.compile(r"/quest/(?!explore/)[^/]+/[^/?]+")

def dismiss_blocking_dialogs(page: Page) -> None:
    for _ in range(3):
        dialog = page.get_by_role("dialog")
        if dialog.count() == 0:
            break
        dialog.get_by_role("button").first.click()
def open_homepage(page: Page):
    page.goto(get_base_url())


def assert_quest_detail_loaded(page: Page, card_title: str):
    expect(page).to_have_title(re.compile(re.escape(card_title)))
    dismiss_blocking_dialogs(page)
    expect(page.locator("main").get_by_text(card_title, exact=True).first).to_be_visible() 

def test_homepage_to_explore_to_quest_detail(page: Page):
    open_homepage(page)
    explore_page = ExploreQuestPage(page)
    explore_page.open_all_quests()
    card_title = explore_page.open_first_quest_detail()
    assert_quest_detail_loaded(page, card_title)

def test_explore_all_should_show_all_quests(page: Page):
    open_homepage(page)
    explore_page = ExploreQuestPage(page)
    explore_page.open_all_quests()
    quest_cards= explore_page.get_quest_cards()
    expect(quest_cards.first).to_be_visible()
    card_count = quest_cards.count()
    print(f"card_count: {card_count}")
    assert card_count > 0
    




