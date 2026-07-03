import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import BrowserContext, Page, sync_playwright

from pages.metamask_page import MetamaskPage

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
def username():
    print("\n前置准备数据")
    yield "summer"
    print("\n后置清理数据")
