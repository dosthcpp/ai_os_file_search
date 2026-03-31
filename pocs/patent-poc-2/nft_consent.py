import hashlib
import time
import json

class NFTConsentEngine:
    """Mockup for NFT-based Blockchain Consent System (Hyperledger logic)"""
    def __init__(self):
        self.ledger = [] # Simulated Distributed Ledger

    def sign_document(self, user_id: str, content: str):
        # 1. Integrity Check (Hash)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # 2. NFT Minting (Simulated)
        nft_id = f"NFT-CONSENT-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        
        # 3. AI Behavioral Verification (Mock)
        # Analyzing signature speed/patterns
        behavior_score = 0.98 # Normal pattern
        
        entry = {
            "nft_id": nft_id,
            "user_id": user_id,
            "timestamp": time.ctime(),
            "content_hash": content_hash,
            "verification": "AI_VERIFIED" if behavior_score > 0.9 else "FLAGGED",
            "status": "VALID"
        }
        
        self.ledger.append(entry)
        return entry

if __name__ == "__main__":
    engine = NFTConsentEngine()
    print("--- Signing E-Consent Form ---")
    result = engine.sign_document("Tony001", "I agree to the terms and conditions of AI OS Patent PoC.")
    print(json.dumps(result, indent=2))
