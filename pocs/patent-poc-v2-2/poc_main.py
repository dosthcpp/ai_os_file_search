import hashlib
import json


class NFTConsentBlockchain:
    """PoC for NFT Blockchain E-Consent using a simple linked-block ledger."""

    def __init__(self):
        self.ledger: list[dict] = []

    def _hash_block(self, block: dict) -> str:
        """Compute SHA-256 over the block's data and prev_hash fields."""
        payload = json.dumps(block["data"], sort_keys=True) + block["prev_hash"]
        return hashlib.sha256(payload.encode()).hexdigest()

    def mint_consent_nft(self, teacher_id: str, title: str) -> dict:
        """Create a new consent NFT token in PENDING_SIGNATURE state."""
        nft_id = hashlib.sha1(f"{teacher_id}{title}".encode()).hexdigest()[:8]
        return {
            "nft_id": f"CONSENT-{nft_id}",
            "owner":  teacher_id,
            "title":  title,
            "status": "PENDING_SIGNATURE",
        }

    def smart_contract_sign(
        self, nft: dict, parent_id: str, signature_pattern: list[float]
    ) -> dict:
        """
        Finalize a consent NFT via smart contract logic.
        Verifies biometric signature integrity, updates ownership,
        and appends a hashed block to the ledger.
        """
        # AI behavioral verification: a valid signature needs more than 5 data points
        integrity = "VERIFIED" if len(signature_pattern) > 5 else "FLAGGED"

        nft["owner"]     = parent_id
        nft["status"]    = "COMPLETED"
        nft["integrity"] = integrity

        # Link to the previous block (genesis uses "0" * 64)
        prev_hash = self.ledger[-1]["block_hash"] if self.ledger else "0" * 64

        block: dict = {"data": nft, "prev_hash": prev_hash}
        block["block_hash"] = self._hash_block(block)

        self.ledger.append(block)
        return block


class LedgerViewer:
    """Utility for inspecting and validating a NFTConsentBlockchain ledger."""

    def __init__(self, blockchain: NFTConsentBlockchain):
        self.blockchain = blockchain

    def print_summary(self) -> None:
        """Print a formatted summary of every block in the ledger."""
        ledger = self.blockchain.ledger
        print(f"\n{'='*60}")
        print(f"  LEDGER SUMMARY  —  {len(ledger)} block(s)")
        print(f"{'='*60}")
        for idx, block in enumerate(ledger):
            nft    = block["data"]
            status = nft.get("status", "—")
            icon   = "✓" if nft.get("integrity") == "VERIFIED" else "✗"
            print(f"\n  Block #{idx}")
            print(f"    NFT ID    : {nft.get('nft_id')}")
            print(f"    Title     : {nft.get('title')}")
            print(f"    Owner     : {nft.get('owner')}")
            print(f"    Status    : {status}")
            print(f"    Integrity : {icon}  {nft.get('integrity')}")
            print(f"    Prev Hash : {block['prev_hash'][:16]}...")
            print(f"    Block Hash: {block['block_hash'][:16]}...")
        print(f"\n{'='*60}\n")

    def validate_chain(self) -> dict:
        """
        Re-compute each block's hash and verify it matches the stored value,
        and that each block's prev_hash matches the previous block's block_hash.
        Returns a validation report.
        """
        ledger = self.blockchain.ledger
        errors: list[str] = []

        for idx, block in enumerate(ledger):
            # Verify stored block_hash is correct
            expected_hash = self.blockchain._hash_block(
                {"data": block["data"], "prev_hash": block["prev_hash"]}
            )
            if expected_hash != block["block_hash"]:
                errors.append(f"Block #{idx}: hash mismatch — data may have been tampered with.")

            # Verify linkage to previous block
            if idx > 0:
                expected_prev = ledger[idx - 1]["block_hash"]
                if block["prev_hash"] != expected_prev:
                    errors.append(
                        f"Block #{idx}: prev_hash does not match block #{idx - 1} hash — chain broken."
                    )

        is_valid = len(errors) == 0
        return {
            "chain_valid": is_valid,
            "blocks_checked": len(ledger),
            "errors": errors,
            "status": "INTEGRITY OK" if is_valid else "INTEGRITY COMPROMISED",
        }


if __name__ == "__main__":
    bc = NFTConsentBlockchain()

    # --- Mint and sign two consent forms ---
    nft1 = bc.mint_consent_nft("Teacher01", "Field Trip Consent")
    print(f"Minted: {nft1}")
    block1 = bc.smart_contract_sign(nft1, "Parent01", [0.1, 0.5, 0.9, 1.2, 1.5, 2.0])
    print(f"Signed and Committed Block 1: {json.dumps(block1, indent=2)}")

    nft2 = bc.mint_consent_nft("Teacher02", "School Bus Registration")
    print(f"\nMinted: {nft2}")
    block2 = bc.smart_contract_sign(nft2, "Parent02", [1.0, 1.5])  # short pattern → FLAGGED
    print(f"Signed and Committed Block 2: {json.dumps(block2, indent=2)}")

    # --- Ledger viewer ---
    viewer = LedgerViewer(bc)
    viewer.print_summary()

    # --- Chain integrity validation ---
    print("=== Chain Integrity Validation ===")
    report = viewer.validate_chain()
    print(json.dumps(report, indent=2))
