import os
import re
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import BrowserContext, Page, sync_playwright
from pages.galxe_login_page import GalxeLoginPage
from pages.metamask_page import MetamaskPage
from utils.config import get_base_url

load_dotenv()
ROOT = Path(__file__).resolve().parent


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def metamask_context(playwright_instance) -> BrowserContext:
    extension_path = Path(
        os.getenv("METAMASK_EXTENSION_PATH", "extensions/metamask")
    ).resolve()
    profile_path = Path(
        os.getenv("METAMASK_PROFILE_PATH", "profiles/metamask")
    ).resolve()
    profile_path.mkdir(parents=True, exist_ok=True)

    context = playwright_instance.chromium.launch_persistent_context(
        user_data_dir=str(profile_path),
        headless=False,
        args=[
            f"--disable-extensions-except={extension_path}",
            f"--load-extension={extension_path}",
        ],
    )
    metamask = MetamaskPage(context)
    metamask.init_wallet(
        os.getenv("METAMASK_MNEMONIC", "").strip(),
        os.getenv("METAMASK_PASSWORD", ""),
    )
    if metamask.page and not metamask.page.is_closed():
        metamask.page.close()
        metamask.page = None
    yield context
    context.close()


@pytest.fixture
def context(metamask_context: BrowserContext) -> BrowserContext:
    return metamask_context


@pytest.fixture
def page(context: BrowserContext) -> Page:
    galxe_page = context.new_page()
    galxe_page.bring_to_front()
    yield galxe_page
    galxe_page.close()


@pytest.fixture
def guest_page(playwright_instance) -> Page:
    browser = playwright_instance.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.bring_to_front()
    yield page
    context.close()
    browser.close()


@pytest.fixture
def logged_in_page(page, context):
    galxe_login = GalxeLoginPage(page)
    page.goto(get_base_url(), wait_until="load")
    page.bring_to_front()
    login_button = page.get_by_role("banner").get_by_role(
        "button", name=re.compile(r"Log in|Login", re.I)
    )
    if login_button.is_visible(timeout=5_000):
        galxe_login.click_login_button()
        popup = galxe_login.choose_metamask(context)
        metamask = MetamaskPage(context)
        if metamask.approve_popup(popup) == "connect":
            sign_popup = context.wait_for_event("page", timeout=30_000)
            metamask.approve_popup(sign_popup)
    galxe_login.assert_login_success()
    yield page
