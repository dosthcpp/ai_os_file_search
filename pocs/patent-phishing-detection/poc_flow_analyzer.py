import json
import os
import re
from typing import Dict, Any, List

class UnifiedIndexerAndAudit:
    """
    Unified Indexing & Audit Engine (Patent PoC)
    Demonstrates the 'Single-Pass Background Processing' of search metadata and security risk.
    """
    def __init__(self):
        self.search_index = {} # Simulated vector DB/Search index
        self.security_rules = {
            "SEND_SMS": 25,
            "RECEIVE_SMS": 25,
            "SYSTEM_OVERLAY": 30,
            "READ_LOGS": 15,
            "DELETE_PACKAGES": 20
        }
        self.phishing_keywords = ["Toss", "Bank", "Police", "Prosecutor", "Account", "Loan"]

    def analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Performs unified search indexing and security audit in a single pass.
        """
        print(f"[UNIFIED ENGINE] Processing: {file_path}")
        
        # 1. Search Indexing: Extract basic metadata and keywords
        ext = os.path.splitext(file_path)[1].lower()
        search_metadata = {
            "path": file_path,
            "ext": ext,
            "content_preview": content[:100],
            "keywords": self._extract_keywords(content)
        }

        # 2. Security Audit: Analyze risk indicators (Voice Phishing specific)
        security_report = self._perform_security_audit(content)

        # 3. Unified Result: Combine metadata for the search index
        indexed_entry = {
            **search_metadata,
            **security_report
        }

        # Simulate saving to index
        self.search_index[file_path] = indexed_entry
        return indexed_entry

    def _extract_keywords(self, content: str) -> List[str]:
        # Simple regex keyword extraction for indexing
        return list(set(re.findall(r'\b\w{4,}\b', content)))

    def _perform_security_audit(self, content: str) -> Dict[str, Any]:
        risk_score = 0
        findings = []
        
        # Check permissions/API calls
        for indicator, weight in self.security_rules.items():
            if indicator in content:
                risk_score += weight
                findings.append(f"Suspicious indicator detected: {indicator}")

        # Check for phishing keywords in UI strings/metadata
        for kw in self.phishing_keywords:
            if kw.lower() in content.lower():
                risk_score += 15
                findings.append(f"Phishing-related keyword detected: {kw}")

        # Determine threat level
        threat_level = "SAFE"
        if risk_score > 70:
            threat_level = "CRITICAL"
        elif risk_score > 30:
            threat_level = "WARNING"

        return {
            "threat_level": threat_level,
            "risk_score": risk_score,
            "security_findings": findings,
            "security_audit_alert": f"VOICE_PHISHING_{threat_level}" if threat_level != "SAFE" else None
        }

if __name__ == "__main__":
    engine = UnifiedIndexerAndAudit()

    # Case 1: Benign File
    benign_content = "Hello world! This is a simple document for the AI OS project."
    print("\n--- Processing Benign File ---")
    print(json.dumps(engine.analyze_file("doc1.txt", benign_content), indent=2))

    # Case 2: Suspicious Voice Phishing App (Simulated Manifest/Code)
    phishing_content = """
    package_name: com.bank.secure.helper
    permissions: [SEND_SMS, READ_LOGS, SYSTEM_OVERLAY]
    strings: ["Your Toss account is compromised", "Enter bank password"]
    """
    print("\n--- Processing Suspicious File ---")
    print(json.dumps(engine.analyze_file("malicious_app.apk", phishing_content), indent=2))
