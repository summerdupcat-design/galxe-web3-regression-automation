import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

GRAPHQL_URL = os.getenv(
    "GALXE_GRAPHQL_URL",
    "https://graphigo.stg.galaxy.eco/query",
)
QUEST_CLAIM_QUERY = """
query QuestClaimSection($id: ID!, $address: String!, $withAddress: Boolean!) {
  campaign(id: $id) {
    id
    loyaltyPoints
    whitelistInfo(address: $address) {
      claimedLoyaltyPoints
      __typename
    }
    userParticipants(address: $address, first: 1) @include(if: $withAddress) {
      list {
        status
        __typename
      }
    }
  }
}
"""


class GalxeAPI:
    def __init__(self, graphql_url: str = GRAPHQL_URL):
        self.graphql_url = graphql_url

    def get_quest_claim_info(self, campaign_id: str, wallet_address: str) -> dict[str, Any]:
        address = self._format_address(wallet_address)
        payload = {
            "operationName": "QuestClaimSection",
            "variables": {
                "id": campaign_id,
                "address": address,
                "withAddress": True,
            },
            "query": QUEST_CLAIM_QUERY,
        }
        data = self._post(payload)
        campaign = data["campaign"]
        if campaign is None:
            raise AssertionError(f"Campaign not found: {campaign_id}")

        whitelist = campaign.get("whitelistInfo") or {}
        participants = campaign.get("userParticipants") or {}
        participant_list = participants.get("list") or []

        return {
            "campaign_id": campaign["id"],
            "loyalty_points": campaign.get("loyaltyPoints"),
            "claimed_loyalty_points": whitelist.get("claimedLoyaltyPoints"),
            "participant_status": (
                participant_list[0].get("status") if participant_list else None
            ),
        }

    def wait_for_claimed_points(
        self,
        campaign_id: str,
        wallet_address: str,
        *,
        expected_claimed_points: int,
        timeout: float = 15,
        poll_interval: float = 1,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        last_info: dict[str, Any] | None = None

        while time.monotonic() < deadline:
            last_info = self.get_quest_claim_info(campaign_id, wallet_address)
            claimed = last_info.get("claimed_loyalty_points")
            if claimed is not None and int(claimed) == expected_claimed_points:
                return last_info
            time.sleep(poll_interval)

        raise AssertionError(
            "Claimed loyalty points did not update in time. "
            f"expected={expected_claimed_points}, last={last_info}"
        )

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.graphql_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            raise AssertionError(
                f"GraphQL request failed: {error.code} {error.reason}"
            ) from error

        if body.get("errors"):
            raise AssertionError(f"GraphQL errors: {body['errors']}")
        return body["data"]

    @staticmethod
    def _format_address(wallet_address: str) -> str:
        address = wallet_address.strip()
        if address.startswith("EVM:"):
            return address
        if not address.startswith("0x"):
            address = f"0x{address}"
        return f"EVM:{address}"
