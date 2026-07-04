from tests.fixtures.claim_samples import (
    SAMPLE_CAMPAIGN_ID,
    SAMPLE_CLAIMED_POINTS,
    SAMPLE_WALLET_ADDRESS,
    SUCCESS_TX_EXPLORER_URL,
    SUCCESS_TX_HASH,
)
from utils.claim_assertions import ClaimAssertions
from utils.galxe_api import GalxeAPI
from utils.gravity_chain import GravityChainClient, extract_tx_hash


def test_extract_tx_hash_from_explorer_url():
    assert extract_tx_hash(SUCCESS_TX_EXPLORER_URL) == SUCCESS_TX_HASH


def test_chain_assert_claim_transaction():
    details = GravityChainClient().assert_claim_transaction(
        SUCCESS_TX_HASH,
        expected_to=SAMPLE_WALLET_ADDRESS,
        expected_points=SAMPLE_CLAIMED_POINTS,
    )

    assert details.status == 1
    assert details.from_address.lower() == SAMPLE_WALLET_ADDRESS.lower()
    assert details.to_address.lower() == SAMPLE_WALLET_ADDRESS.lower()
    assert details.amount == SAMPLE_CLAIMED_POINTS * 10**18
    assert details.contract_to == "0x513f994b48db27aecc2950f4a60e45cac09398e8"


def test_api_assert_claimed_loyalty_points():
    claim_info = GalxeAPI().get_quest_claim_info(
        SAMPLE_CAMPAIGN_ID,
        SAMPLE_WALLET_ADDRESS,
    )

    assert claim_info["campaign_id"] == SAMPLE_CAMPAIGN_ID
    assert claim_info["loyalty_points"] == SAMPLE_CLAIMED_POINTS
    assert claim_info["claimed_loyalty_points"] == SAMPLE_CLAIMED_POINTS


def test_full_claim_assertions_with_sample_data():
    claim_info, chain_details = ClaimAssertions().assert_full_claim(
        campaign_id=SAMPLE_CAMPAIGN_ID,
        wallet_address=SAMPLE_WALLET_ADDRESS,
        tx_hash=SUCCESS_TX_HASH,
        expected_points=SAMPLE_CLAIMED_POINTS,
        api_timeout=5,
    )

    assert claim_info["claimed_loyalty_points"] == SAMPLE_CLAIMED_POINTS
    assert chain_details.tx_hash == SUCCESS_TX_HASH
