from pathlib import Path
import shutil

METAMASK_EXTENSION_ID = "nkbihfbeogaeaoehlefnkodbefgpgknn"
CHROME_EXTENSIONS_ROOT = Path.home()/("Library/Application Support/Google/Chrome/Default/Extensions")
TARGET_DIR = Path("extensions/metamask")

def find_latest_metamask_version()-> Path:
    metamask_root = CHROME_EXTENSIONS_ROOT/METAMASK_EXTENSION_ID

    if not metamask_root.exists():
        raise FileNotFoundError(f"Metamask extension not found at {metamask_root}")

    versions = [p for p in metamask_root.iterdir() if p.is_dir()]
    if not versions:
        raise FileNotFoundError(f"找到了 MetaMask 插件目录，但里面没有版本目录:{metamask_root}")

    return sorted(versions)[-1]

def export_metamask_extension():
    latest_version = find_latest_metamask_version()
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)

    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(latest_version, TARGET_DIR)

    print(f"MetaMask 已导出到: {TARGET_DIR.resolve()}")
    print(f"来源目录: {latest_version}")

if __name__ == "__main__":
    export_metamask_extension()