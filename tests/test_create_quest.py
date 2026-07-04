from pages.create_quest_page import QUEST_DETAIL_URL


def test_create_quest(create_quest):
    quest = create_quest()

    assert QUEST_DETAIL_URL.search(quest["url"])
    assert quest["title"]
