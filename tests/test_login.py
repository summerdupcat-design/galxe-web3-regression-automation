import allure
from playwright.sync_api import BrowserContext, TimeoutError

from pages.galxe_login_page import GalxeLoginPage
from pages.metamask_page import MetamaskPage
from utils.config import get_base_url


@allure.title("用户可以使用MetaMask登录Galxe")
@allure.feature("登录")
@allure.story("Metamask登录")
def test_user_can_login_with_metamask(logged_out_page, context: BrowserContext):
    page = logged_out_page
    metamask = MetamaskPage(context)
    metamask.ensure_unlocked()

    page.goto(get_base_url(), wait_until="load")
    page.bring_to_front()

    galxe_login = GalxeLoginPage(page)
    galxe_login.login_with_metamask(context)
