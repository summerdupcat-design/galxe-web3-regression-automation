from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from pages.metamask_page import MetamaskPage, WalletState

load_dotenv()


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"环境变量 {name} 未设置")
    return value


def main() -> None:
    extension_path = Path(get_env("METAMASK_EXTENSION_PATH")).resolve()
    profile_path = Path(get_env("METAMASK_PROFILE_PATH")).resolve()
    password = get_env("METAMASK_PASSWORD")
    mnemonic = os.getenv("METAMASK_MNEMONIC", "").strip()

    if not extension_path.exists():
        raise FileNotFoundError(f"MetaMask 扩展不存在: {extension_path}")
    profile_path.mkdir(parents=True, exist_ok=True)

    extension_arg = str(extension_path)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=False,
            slow_mo=300,
            args=[
                f"--disable-extensions-except={extension_arg}",
                f"--load-extension={extension_arg}",
            ],
        )
        metamask = MetamaskPage2(context)

        print("1. 访问 MetaMask...", flush=True)
        metamask.visit()
        print(f"   url={metamask.page.url}", flush=True)

        print("2. 状态判断...", flush=True)
        state = metamask.get_state()
        print(f"   状态={state.value}", flush=True)

        if state is WalletState.LOGGED_IN:
            print("   已有账号且已登录，跳过", flush=True)
        elif state is WalletState.LOCKED:
            print("3. 执行 login()...", flush=True)
            metamask.login(password)
        elif state is WalletState.NEED_CREATE:
            if not mnemonic:
                raise ValueError("无账号需创建，请设置环境变量 METAMASK_MNEMONIC")
            print("4. 执行 create()...", flush=True)
            metamask.create(mnemonic, password)

        final_state = metamask.get_state()
        print(f"完成: 状态={final_state.value}, url={metamask.page.url}", flush=True)
        print("浏览器将在 10 秒后关闭，便于查看最终页面。", flush=True)
        metamask.page.wait_for_timeout(10_000)
        context.close()


if __name__ == "__main__":
    main()
