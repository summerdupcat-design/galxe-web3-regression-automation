import os

from dotenv import load_dotenv

load_dotenv()


def get_base_url() -> str:
    return os.getenv("BASE_URL", "https://app.stg.galxe.com/")


def get_test_wallet_address() -> str:
    return os.getenv(
        "TEST_WALLET_ADDRESS",
        "0xd1b14146B71d921c9E66610E4864ea0dCDa508D9",
    )