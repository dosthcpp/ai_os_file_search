import json
import re

# Mock APK manifest content representing declared permissions
MOCK_APK_MANIFEST = """
<manifest package="com.suspicious.app">
    <uses-permission android:name="android.permission.READ_SMS"/>
    <uses-permission android:name="android.permission.RECEIVE_SMS"/>
    <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
    <application android:label="TotallyLegitApp">
        <activity android:name=".MainActivity"/>
    </application>
</manifest>
"""

# Mock APK string resource file containing embedded URLs
MOCK_APK_STRINGS = """
<resources>
    <string name="api_host">https://api.legitimate-service.com/v1</string>
    <string name="analytics_url">http://track.evil-domain.ru/collect</string>
    <string name="cdn">https://cdn.goodservice.net/assets</string>
    <string name="report_url">http://45.33.32.156/exfil</string>
    <string name="update_check">http://update.phish-site.biz/check</string>
</resources>
"""

# Dangerous permissions with individual risk scores and human-readable reasons
DANGEROUS_PERMISSIONS = {
    "READ_SMS":             {"score": 35, "reason": "Can silently read private SMS messages (OTP theft risk)"},
    "RECEIVE_SMS":          {"score": 25, "reason": "Can intercept incoming SMS in real time"},
    "INSTALL_PACKAGES":     {"score": 40, "reason": "Can silently install additional malicious APKs"},
    "READ_CONTACTS":        {"score": 20, "reason": "Can exfiltrate user contact list"},
    "RECORD_AUDIO":         {"score": 30, "reason": "Can activate microphone without user awareness"},
    "ACCESS_FINE_LOCATION": {"score": 15, "reason": "Precise GPS tracking, possible stalkerware vector"},
}

# URL heuristics: (compiled pattern, description, per-match score)
SUSPICIOUS_URL_PATTERNS = [
    (
        re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}"),
        "Direct IP address endpoint — no domain name, common evasion tactic",
        20,
    ),
    (
        re.compile(r'https?://[^\s"\']*(?:\.ru|\.biz|\.xyz|\.top)[^\s"\']*'),
        "High-risk TLD frequently associated with phishing campaigns",
        20,
    ),
    (
        re.compile(r'https?://[^\s"\']*(?:exfil|track|collect|evil|phish)[^\s"\']*'),
        "Keyword in URL matching known data-exfiltration or phishing patterns",
        20,
    ),
]


class APKStaticAnalyzer:
    """Simulates static analysis of an APK manifest and string resources."""

    def __init__(self, manifest: str, strings: str):
        self.manifest = manifest
        self.strings = strings

    def scan_permissions(self) -> list[dict]:
        """Detect dangerous permission declarations and score each finding."""
        findings = []
        for perm_name, meta in DANGEROUS_PERMISSIONS.items():
            pattern = rf"android\.permission\.{re.escape(perm_name)}"
            if re.search(pattern, self.manifest):
                findings.append({
                    "permission": f"android.permission.{perm_name}",
                    "score":      meta["score"],
                    "reason":     meta["reason"],
                })
        return findings

    def scan_urls(self) -> list[dict]:
        """Detect suspicious URLs embedded in string resources."""
        findings = []
        for compiled_pattern, description, score in SUSPICIOUS_URL_PATTERNS:
            for match in compiled_pattern.findall(self.strings):
                findings.append({
                    "url":    match,
                    "score":  score,
                    "reason": description,
                })
        return findings

    def generate_report(self) -> dict:
        """Aggregate all scan results into a detailed threat-score report."""
        perm_findings = self.scan_permissions()
        url_findings  = self.scan_urls()

        perm_score  = sum(f["score"] for f in perm_findings)
        url_score   = sum(f["score"] for f in url_findings)
        total_score = min(perm_score + url_score, 100)  # cap at 100

        if total_score >= 70:
            threat_level = "CRITICAL"
        elif total_score >= 40:
            threat_level = "WARNING"
        else:
            threat_level = "SAFE"

        return {
            "threat_level":  threat_level,
            "total_score":   total_score,
            "score_breakdown": {
                "permission_score": perm_score,
                "url_score":        url_score,
            },
            "permission_findings": perm_findings,
            "url_findings":        url_findings,
            "summary": (
                f"{len(perm_findings)} dangerous permission(s) and "
                f"{len(url_findings)} suspicious URL(s) detected."
            ),
        }


class AIOS_UnifiedAudit:
    """PoC for AI-Powered E-consent & Phishing Detection"""

    def __init__(self):
        self.sensitive_patterns = {"RRN": r"\d{6}-\d{7}", "Bank": r"\d{10,14}"}

    def process_document(self, text: str) -> dict:
        """Scan document text for sensitive personal information using regex patterns."""
        print("[AI-AUDIT] Scanning for Personal Information...")
        findings = []
        for label, pattern in self.sensitive_patterns.items():
            if re.search(pattern, text):
                findings.append(f"{label} detected")

        risk_level = "CRITICAL" if findings else "SAFE"
        encryption = "RSA-OAEP + AES-256" if risk_level == "CRITICAL" else "None"
        return {"risk": risk_level, "encryption": encryption, "details": findings}

    def analyze_apk(
        self,
        manifest: str = MOCK_APK_MANIFEST,
        strings: str = MOCK_APK_STRINGS,
    ) -> dict:
        """Run static APK analysis on manifest permissions and embedded strings."""
        print("[SANDBOX] Running static APK analysis...")
        analyzer = APKStaticAnalyzer(manifest, strings)
        return analyzer.generate_report()


if __name__ == "__main__":
    audit = AIOS_UnifiedAudit()

    # --- Document audit ---
    print("=== Document Audit ===")
    doc_res = audit.process_document("Consent form for Tony, RRN: 950101-1234567")
    print(json.dumps(doc_res, indent=2))

    # --- APK static analysis ---
    print("\n=== APK Static Analysis Report ===")
    apk_res = audit.analyze_apk()
    print(json.dumps(apk_res, indent=2))
