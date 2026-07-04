import pytest

from pages.metamask_page import MetamaskPage
from pages.quest_claim_page import ClaimResult, QuestClaimPage
from tests.fixtures.claim_samples import (
    SAMPLE_CAMPAIGN_ID,
    SAMPLE_CLAIMED_POINTS,
    SAMPLE_WALLET_ADDRESS,
    SUCCESS_TX_EXPLORER_URL,
    SUCCESS_TX_HASH,
)
from utils.config import get_test_wallet_address
from utils.quest_claim_flow import QuestClaimFlow

LIVE_CLAIM = pytest.mark.skip(
    reason="STG 系统告警，暂不可实战领取；移除 skip 并设置 ENABLE_LIVE_CLAIM=1 后启用"
)


@LIVE_CLAIM
def test_claim_quest_with_credentials_live(logged_in_page, context):
    claim_page = QuestClaimPage(logged_in_page)
    metamask = MetamaskPage(context)

    claim_page.open()
    claim_page.complete_visit_credential(context)
    claim_page.complete_claim(context, metamask)
    claim_page.assert_reward_claimed()


@LIVE_CLAIM
def test_claim_quest_without_credentials_live(
    logged_in_page, context, create_quest_no_credentials
):
    quest_data = create_quest_no_credentials(points="10")

    QuestClaimFlow().run_no_credentials_claim_live(
        page=logged_in_page,
        context=context,
        metamask=MetamaskPage(context),
        quest=quest_data,
        wallet_address=get_test_wallet_address(),
        expected_points=10,
    )


def test_claim_quest_without_credentials_post_claim_flow():
    """无 credential quest：假设领取成功，验证 API + 链上断言流程。"""
    quest = {
        "url": f"https://app.stg.galxe.com/quest/Summertest/{SAMPLE_CAMPAIGN_ID}",
        "title": "Sample claimed quest",
    }
    claim_result = ClaimResult(
        tx_hash=SUCCESS_TX_HASH,
        explorer_url=SUCCESS_TX_EXPLORER_URL,
    )

    claim_info, chain_details = QuestClaimFlow().run_no_credentials_claim_dry_run(
        quest=quest,
        wallet_address=SAMPLE_WALLET_ADDRESS,
        claim_result=claim_result,
        expected_points=SAMPLE_CLAIMED_POINTS,
    )

    assert claim_info["claimed_loyalty_points"] == SAMPLE_CLAIMED_POINTS
    assert chain_details.tx_hash == SUCCESS_TX_HASH


def test_claim_quest_without_credentials_full_flow_dry_run():
    """
    完整流程（dry-run）：
    1. create_quest_no_credentials -> 得到 quest url
    2. open quest detail -> 点击 claim -> MetaMask 签名
    3. 弹窗返回 explorer url -> 提取 tx
    4. API 校验 claimedLoyaltyPoints
    5. 链上校验 status / from / to / amount

    当前使用样本数据模拟步骤 1-3 的输出，仅执行步骤 4-5。
    """
    quest = {
        "url": f"https://app.stg.galxe.com/quest/Summertest/{SAMPLE_CAMPAIGN_ID}",
        "title": "Dry-run quest",
    }
    claim_result = ClaimResult(
        tx_hash=SUCCESS_TX_HASH,
        explorer_url=SUCCESS_TX_EXPLORER_URL,
    )
    flow = QuestClaimFlow()

    claim_info, chain_details = flow.run_no_credentials_claim_dry_run(
        quest=quest,
        wallet_address=SAMPLE_WALLET_ADDRESS,
        claim_result=claim_result,
        expected_points=SAMPLE_CLAIMED_POINTS,
    )

    assert claim_info["loyalty_points"] == SAMPLE_CLAIMED_POINTS
    assert chain_details.status == 1
    assert chain_details.to_address.lower() == SAMPLE_WALLET_ADDRESS.lower()
    assert chain_details.amount == SAMPLE_CLAIMED_POINTS * 10**18
