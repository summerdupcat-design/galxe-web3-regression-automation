from utils.galxe_api import GalxeAPI
from utils.gravity_chain import ClaimTransactionDetails, GravityChainClient


class ClaimAssertions:
    def __init__(
        self,
        galxe_api: GalxeAPI | None = None,
        gravity_chain: GravityChainClient | None = None,
    ):
        self.galxe_api = galxe_api or GalxeAPI()
        self.gravity_chain = gravity_chain or GravityChainClient()

    def assert_claimed_loyalty_points(
        self,
        campaign_id: str,
        wallet_address: str,
        expected_points: int,
        *,
        timeout: float = 15,
    ) -> dict:
        claim_info = self.galxe_api.wait_for_claimed_points(
            campaign_id,
            wallet_address,
            expected_claimed_points=expected_points,
            timeout=timeout,
        )
        assert claim_info["claimed_loyalty_points"] == expected_points
        assert claim_info["loyalty_points"] == expected_points
        return claim_info

    def assert_on_chain_claim(
        self,
        tx_hash: str,
        wallet_address: str,
        expected_points: int,
    ) -> ClaimTransactionDetails:
        details = self.gravity_chain.assert_claim_transaction(
            tx_hash,
            expected_to=wallet_address,
            expected_points=expected_points,
        )
        assert details.status == 1
        assert details.from_address.lower() == wallet_address.lower()
        return details

    def assert_full_claim(
        self,
        *,
        campaign_id: str,
        wallet_address: str,
        tx_hash: str,
        expected_points: int,
        api_timeout: float = 15,
    ) -> tuple[dict, ClaimTransactionDetails]:
        claim_info = self.assert_claimed_loyalty_points(
            campaign_id,
            wallet_address,
            expected_points,
            timeout=api_timeout,
        )
        chain_details = self.assert_on_chain_claim(
            tx_hash,
            wallet_address,
            expected_points,
        )
        return claim_info, chain_details
