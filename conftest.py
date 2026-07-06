import os
import time
from pathlib import Path
from typing import Callable, TypedDict
import allure
import pytest
from dotenv import load_dotenv
from playwright.sync_api import BrowserContext, Page, sync_playwright
from pages.create_quest_page import CreateQuestPage
from pages.galxe_login_page import GalxeLoginPage
from pages.metamask_page import MetamaskPage
from utils.config import get_base_url


class ReleasedQuest(TypedDict):
    url: str
    title: str

load_dotenv()
ROOT = Path(__file__).resolve().parent

BROWSER_MAXIMIZE_ARGS = ["--start-maximized"]


def _maximize_browser(context: BrowserContext) -> None:
    if not context.pages:
        return
    try:
        session = context.new_cdp_session(context.pages[0])
        window = session.send("Browser.getWindowForTarget")
        session.send(
            "Browser.setWindowBounds",
            {
                "windowId": window["windowId"],
                "bounds": {"windowState": "maximized"},
            },
        )
    except Exception:
        pass


def _metamask_launch_args(extension_path: Path) -> list[str]:
    return [
        f"--disable-extensions-except={extension_path}",
        f"--load-extension={extension_path}",
        *BROWSER_MAXIMIZE_ARGS,
    ]


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
        no_viewport=True,
        args=_metamask_launch_args(extension_path),
    )
    _maximize_browser(context)
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
def logged_out_page(page: Page, context: BrowserContext) -> Page:
    metamask = MetamaskPage(context)
    metamask.ensure_unlocked()
    galxe_login = GalxeLoginPage(page)
    galxe_login.ensure_logged_out(context)
    yield page


@pytest.fixture
def guest_page(playwright_instance) -> Page:
    browser = playwright_instance.chromium.launch(
        headless=False,
        args=BROWSER_MAXIMIZE_ARGS,
    )
    context = browser.new_context(no_viewport=True)
    _maximize_browser(context)
    page = context.new_page()
    page.bring_to_front()
    yield page
    context.close()
    browser.close()


@pytest.fixture(autouse=True)
def isolate_browser_context(context: BrowserContext):
    for popup in list(context.pages):
        if popup.is_closed():
            continue
        if "chrome-extension://" in popup.url and "notification.html" in popup.url:
            popup.close()
    yield
    for popup in list(context.pages):
        if popup.is_closed():
            continue
        if "galxe.com" not in popup.url:
            continue
        try:
            GalxeLoginPage(popup).dismiss_blocking_dialogs()
        except Exception:
            pass


@pytest.fixture
def logged_in_page(page, context):
    galxe_login = GalxeLoginPage(page)
    galxe_login.ensure_logged_in(context)
    yield page


@pytest.fixture
def create_quest(logged_in_page: Page, context: BrowserContext) -> Callable[..., ReleasedQuest]:
    def _create_quest(
        *,
        title: str | None = None,
        description: str = "Automated test quest description",
        page_name: str | None = None,
        page_link: str = "https://galxe.com",
        points: str = "10",
    ) -> ReleasedQuest:
        create_page = CreateQuestPage(logged_in_page)
        create_page.open(context=context)

        quest_title = title or f"Test Quest {int(time.time())}"
        create_page.set_quest_info(title=quest_title, description=description)
        create_page.go_to_next_step()

        create_page.set_point_reward()
        create_page.go_to_next_step()

        create_page.set_quest_task_group(
            page_name=page_name or f"Visit Page {int(time.time())}",
            page_link=page_link,
            points=points,
        )
        create_page.disable_participation_requirement()
        quest_url = create_page.release(quest_title)
        return {"url": quest_url, "title": quest_title}

    return _create_quest


@pytest.fixture
def create_quest_no_credentials(
    logged_in_page: Page, context: BrowserContext
) -> Callable[..., ReleasedQuest]:
    def _create_quest_no_credentials(
        *,
        title: str | None = None,
        description: str = "Automated test quest description",
        points: str = "10",
    ) -> ReleasedQuest:
        create_page = CreateQuestPage(logged_in_page)
        create_page.open(context=context)

        quest_title = title or f"Test Quest {int(time.time())}"
        create_page.set_quest_info(title=quest_title, description=description)
        create_page.set_quest_private()
        create_page.go_to_next_step()

        create_page.set_point_reward()
        create_page.go_to_next_step()

        create_page.enable_no_task_requirement(points=points)
        quest_url = create_page.release(quest_title)
        return {"url": quest_url, "title": quest_title}

    return _create_quest_no_credentials

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    # 只对测试用例的实际执行失败结果进行截图
    if report.when != "call":
        return
    if report.failed:
        # 获取当前页面的截图
        page = item.funcargs.get("page")
        if page:
            screenshot = page.screenshot(full_page=True)
            allure.attach(
                screenshot,
                name="Failure Screenshot",
                attachment_type=allure.attachment_type.PNG,
            )