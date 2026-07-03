import re

from playwright.sync_api import BrowserContext, Page, expect

from pages.galxe_login_page import GalxeLoginPage
from pages.metamask_page import MetamaskPage
from utils.config import get_base_url


def test_user_can_login_with_metamask(page: Page, context: BrowserContext):
    metamask = MetamaskPage(context)
    page.goto(get_base_url(), wait_until="load")
    page.bring_to_front()
    expect(page.get_by_role("banner")).to_be_visible(timeout=30_000)

    galxe_login = GalxeLoginPage(page)
    galxe_login.click_login_button()

    with context.expect_page() as popup_info:
        galxe_login.choose_metamask()
    popup = popup_info.value

    if metamask.approve_popup(popup) == "connect":
        sign_popup = context.wait_for_event("page", timeout=30_000)
        metamask.approve_popup(sign_popup)

    expect(page.get_by_role("button", name=re.compile(r"Log in|Login", re.I))).not_to_be_visible(
        timeout=30_000
    )
