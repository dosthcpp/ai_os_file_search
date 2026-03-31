# Patent PoC 2 — NFT Blockchain Mobile E-Consent

## Invention Title
Mobile e-consent form using NFT blockchain technology and AI technology

---

## Overview
This PoC simulates a Hyperledger Fabric-inspired consent workflow where each signed consent form is tokenized as a unique NFT and appended to an immutable linked-block ledger. Each block stores a SHA-256 hash of its content and a pointer to the previous block's hash, enabling end-to-end chain integrity validation.

---

## Key Classes

| Class | Role |
|---|---|
| `NFTConsentBlockchain` | Mints consent NFTs and appends signed blocks to the ledger |
| `LedgerViewer` | Prints a formatted ledger summary and validates hash integrity |

---

## Workflow

```
Teacher → mint_consent_nft()  →  PENDING_SIGNATURE NFT
Parent  → smart_contract_sign() →  COMPLETED block appended to ledger
Admin   → LedgerViewer.print_summary()  →  Formatted audit trail
Admin   → LedgerViewer.validate_chain() →  Hash integrity report
```

---

## Block Structure

```json
{
  "data": {
    "nft_id": "CONSENT-abc12345",
    "title":  "Field Trip Consent",
    "owner":  "Parent01",
    "status": "COMPLETED",
    "integrity": "VERIFIED"
  },
  "prev_hash": "<hash of previous block>",
  "block_hash": "<SHA-256 of data + prev_hash>"
}
```

The genesis block uses `"0" * 64` as `prev_hash`.

---

## LedgerViewer

### `print_summary()`
Prints a human-readable table of all minted and signed NFT consents, including NFT ID, title, owner, status, and integrity flag.

### `validate_chain() → dict`
Re-computes every block's SHA-256 hash and verifies:
1. Each stored `block_hash` matches the re-computed value (tamper detection).
2. Each `prev_hash` matches the previous block's `block_hash` (chain linkage).

Returns:
```json
{
  "chain_valid": true,
  "blocks_checked": 2,
  "errors": [],
  "status": "INTEGRITY OK"
}
```

---

## Biometric Integrity Check
A signature pattern with **≤ 5 data points** is flagged as `FLAGGED`; patterns with **> 5 points** are marked `VERIFIED`. This simulates AI behavioral anomaly detection on stylus/touch pressure sequences.

---

## Usage
```bash
python poc_main.py
```

---

## Dependencies
- Python 3.11+ (stdlib only — `hashlib`, `json`)
