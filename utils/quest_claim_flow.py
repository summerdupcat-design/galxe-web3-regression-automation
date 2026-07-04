from pages.quest_claim_page import ClaimResult, QuestClaimPage
from utils.claim_assertions import ClaimAssertions
from utils.galxe_api import GalxeAPI
from utils.gravity_chain import ClaimTransactionDetails, extract_campaign_id


class QuestClaimFlow:
    """Quest 领取流程编排：UI 操作 + 领取后 API / 链上断言。"""

    def __init__(self, claim_assertions: ClaimAssertions | None = None):
        self.claim_assertions = claim_assertions or ClaimAssertions()
        self.galxe_api = self.claim_assertions.galxe_api

    def assert_not_claimed_yet(self, campaign_id: str, wallet_address: str) -> dict:
        claim_info = self.galxe_api.get_quest_claim_info(campaign_id, wallet_address)
        claimed = claim_info.get("claimed_loyalty_points")
        assert claimed in (None, 0), (
            f"Quest already claimed before test claim: {claim_info}"
        )
        return claim_info

    def open_quest_detail(
        self,
        page,
        quest_url: str,
        *,
        require_credential: bool,
    ) -> QuestClaimPage:
        claim_page = QuestClaimPage(page)
        claim_page.open(quest_url, require_credential=require_credential)
        return claim_page

    def execute_claim(
        self,
        claim_page: QuestClaimPage,
        context,
        metamask,
    ) -> ClaimResult:
        return claim_page.complete_claim(context, metamask)

    def verify_after_claim(
        self,
        *,
        quest_url: str,
        wallet_address: str,
        claim_result: ClaimResult,
        expected_points: int,
        api_timeout: float = 15,
    ) -> tuple[dict, ClaimTransactionDetails]:
        assert claim_result.tx_hash, "Claim tx hash is required for verification"

        campaign_id = extract_campaign_id(quest_url)
        return self.claim_assertions.assert_full_claim(
            campaign_id=campaign_id,
            wallet_address=wallet_address,
            tx_hash=claim_result.tx_hash,
            expected_points=expected_points,
            api_timeout=api_timeout,
        )

    def run_no_credentials_claim_live(
        self,
        *,
        page,
        context,
        metamask,
        quest: dict[str, str],
        wallet_address: str,
        expected_points: int,
    ) -> tuple[ClaimResult, dict, ClaimTransactionDetails]:
        campaign_id = extract_campaign_id(quest["url"])
        self.assert_not_claimed_yet(campaign_id, wallet_address)

        claim_page = self.open_quest_detail(
            page,
            quest["url"],
            require_credential=False,
        )
        claim_result = self.execute_claim(claim_page, context, metamask)
        claim_info, chain_details = self.verify_after_claim(
            quest_url=quest["url"],
            wallet_address=wallet_address,
            claim_result=claim_result,
            expected_points=expected_points,
        )
        return claim_result, claim_info, chain_details

    def run_no_credentials_claim_dry_run(
        self,
        *,
        quest: dict[str, str],
        wallet_address: str,
        claim_result: ClaimResult,
        expected_points: int,
    ) -> tuple[dict, ClaimTransactionDetails]:
        """假设 UI 领取已成功，仅执行领取后的 API / 链上断言。"""
        return self.verify_after_claim(
            quest_url=quest["url"],
            wallet_address=wallet_address,
            claim_result=claim_result,
            expected_points=expected_points,
            api_timeout=5,
        )
