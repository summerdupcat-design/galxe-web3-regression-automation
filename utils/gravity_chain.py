import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

GRAVITY_RPC_URL = os.getenv(
    "GRAVITY_RPC_URL",
    "https://mainnet-rpc.gravity.xyz/",
)
GRAVITY_EXPLORER_TX_PATTERN = re.compile(
    r"/tx/(0x[a-fA-F0-9]{64})",
    re.I,
)
CLAIM_EVENT_TOPIC = (
    "0x38865f98efc59856e024850c4f92cd97cad5af306dd7c244ad9dff1a88bc74e3"
)
POINTS_DECIMALS = 18


@dataclass
class ClaimTransactionDetails:
    tx_hash: str
    status: int
    from_address: str
    to_address: str
    amount: int
    contract_to: str


class GravityChainClient:
    def __init__(self, rpc_url: str = GRAVITY_RPC_URL):
        self.rpc_url = rpc_url

    def assert_claim_transaction(
        self,
        tx_hash: str,
        *,
        expected_to: str,
        expected_points: int,
    ) -> ClaimTransactionDetails:
        receipt = self.get_transaction_receipt(tx_hash)
        transaction = self.get_transaction(tx_hash)
        details = self.parse_claim_transaction(receipt, transaction)

        assert details.status == 1, f"Transaction failed: {tx_hash}"
        assert details.to_address.lower() == expected_to.lower(), (
            f"Unexpected claim recipient. expected={expected_to}, "
            f"actual={details.to_address}"
        )
        assert details.amount == expected_points * (10**POINTS_DECIMALS), (
            f"Unexpected claim amount. expected={expected_points} "
            f"({expected_points * 10**POINTS_DECIMALS}), actual={details.amount}"
        )
        return details

    def get_transaction_receipt(self, tx_hash: str) -> dict:
        return self._rpc("eth_getTransactionReceipt", [tx_hash])

    def get_transaction(self, tx_hash: str) -> dict:
        return self._rpc("eth_getTransactionByHash", [tx_hash])

    def parse_claim_transaction(
        self,
        receipt: dict,
        transaction: dict,
    ) -> ClaimTransactionDetails:
        if receipt is None or transaction is None:
            raise AssertionError("Transaction not found on chain")

        status = int(receipt.get("status", "0x0"), 16)
        from_address = transaction["from"]
        contract_to = transaction["to"]

        claim_log = self._find_claim_event_log(receipt.get("logs", []))
        if claim_log is None:
            raise AssertionError(
                f"Claim event not found in transaction logs: {transaction['hash']}"
            )

        data = bytes.fromhex(claim_log["data"][2:])
        recipient = "0x" + data[32:64][-20:].hex()
        amount = int.from_bytes(data[64:96], "big")

        return ClaimTransactionDetails(
            tx_hash=transaction["hash"],
            status=status,
            from_address=from_address,
            to_address=recipient,
            amount=amount,
            contract_to=contract_to,
        )

    def _find_claim_event_log(self, logs: list[dict]) -> dict | None:
        topic = CLAIM_EVENT_TOPIC.lower()
        for log in logs:
            topics = log.get("topics") or []
            if topics and topics[0].lower() == topic:
                return log
        return None

    def _rpc(self, method: str, params: list) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        request = urllib.request.Request(
            self.rpc_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            raise AssertionError(
                f"RPC request failed: {error.code} {error.reason}"
            ) from error

        if body.get("error"):
            raise AssertionError(f"RPC error: {body['error']}")
        return body.get("result")


def extract_tx_hash(explorer_url: str) -> str:
    match = GRAVITY_EXPLORER_TX_PATTERN.search(explorer_url)
    if not match:
        raise AssertionError(f"Unable to extract tx hash from URL: {explorer_url}")
    return match.group(1)


def extract_campaign_id(quest_url: str) -> str:
    match = re.search(r"/quest/[^/]+/([^/?]+)", quest_url)
    if not match:
        raise AssertionError(f"Unable to extract campaign id from URL: {quest_url}")
    return match.group(1)
