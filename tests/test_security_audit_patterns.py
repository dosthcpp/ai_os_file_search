"""
Security Audit - Malicious Pattern Test Suite
==============================================
Tests for dangerous permissions and phishing URL detection
in the /api/security/audit endpoint logic (server/main.py).

Covers 15+ distinct malicious pattern cases:
  - Dangerous Android permissions (6 types)
  - Phishing / suspicious URL patterns (5 patterns)
  - Combined CRITICAL scenarios
  - PI (personally identifiable info) detection
  - Edge cases and clean baseline
"""

import sys
from pathlib import Path

import pytest

# Allow importing server/main.py directly for isolated logic testing
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "server"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def audit(manifest: str = "", strings: str = "", document_text: str = "") -> dict:
    resp = client.post(
        "/api/security/audit",
        json={"manifest": manifest, "strings": strings, "document_text": document_text},
    )
    assert resp.status_code == 200
    return resp.json()


# ─── Baseline ───────────────────────────────────────────────────────────────

class TestCleanBaseline:
    def test_empty_inputs_are_safe(self):
        """No manifest, no strings, no document → all SAFE."""
        result = audit()
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "SAFE"
        assert apk["total_score"] == 0
        assert apk["permission_findings"] == []
        assert apk["url_findings"] == []
        assert result["pi_analysis"]["risk"] == "SAFE"

    def test_benign_manifest_is_safe(self):
        """Harmless permissions (INTERNET, VIBRATE) produce no findings."""
        manifest = """<manifest package="com.example.app">
            <uses-permission android:name="android.permission.INTERNET"/>
            <uses-permission android:name="android.permission.VIBRATE"/>
        </manifest>"""
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "SAFE"
        assert apk["permission_findings"] == []


# ─── Dangerous Permissions ───────────────────────────────────────────────────

class TestDangerousPermissions:
    """Each permission is tested in isolation to verify individual scoring."""

    def test_tc01_read_sms_detected(self):
        """TC-01: READ_SMS (score 35) → SAFE individually, present in findings."""
        manifest = '<uses-permission android:name="android.permission.READ_SMS"/>'
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        perms = {f["permission"] for f in apk["permission_findings"]}
        assert "android.permission.READ_SMS" in perms
        scores = {f["permission"]: f["score"] for f in apk["permission_findings"]}
        assert scores["android.permission.READ_SMS"] == 35
        # 35 < 40 → SAFE alone
        assert apk["threat_level"] == "SAFE"

    def test_tc02_install_packages_warning(self):
        """TC-02: INSTALL_PACKAGES (score 40) alone triggers WARNING threshold."""
        manifest = '<uses-permission android:name="android.permission.INSTALL_PACKAGES"/>'
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "WARNING"
        assert apk["score_breakdown"]["permission_score"] == 40
        reason_found = any("install" in f["reason"].lower() for f in apk["permission_findings"])
        assert reason_found

    def test_tc03_receive_sms_detected(self):
        """TC-03: RECEIVE_SMS (score 25) intercepting incoming OTPs."""
        manifest = '<uses-permission android:name="android.permission.RECEIVE_SMS"/>'
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        perms = {f["permission"] for f in apk["permission_findings"]}
        assert "android.permission.RECEIVE_SMS" in perms
        assert apk["score_breakdown"]["permission_score"] == 25

    def test_tc04_record_audio_microphone_risk(self):
        """TC-04: RECORD_AUDIO (score 30) — silent mic activation."""
        manifest = '<uses-permission android:name="android.permission.RECORD_AUDIO"/>'
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        perms = {f["permission"] for f in apk["permission_findings"]}
        assert "android.permission.RECORD_AUDIO" in perms
        assert apk["score_breakdown"]["permission_score"] == 30

    def test_tc05_read_contacts_exfil(self):
        """TC-05: READ_CONTACTS (score 20) — contact list exfiltration."""
        manifest = '<uses-permission android:name="android.permission.READ_CONTACTS"/>'
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        perms = {f["permission"] for f in apk["permission_findings"]}
        assert "android.permission.READ_CONTACTS" in perms
        assert apk["score_breakdown"]["permission_score"] == 20

    def test_tc06_fine_location_stalkerware(self):
        """TC-06: ACCESS_FINE_LOCATION (score 15) — GPS stalkerware vector."""
        manifest = '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>'
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        perms = {f["permission"] for f in apk["permission_findings"]}
        assert "android.permission.ACCESS_FINE_LOCATION" in perms
        assert apk["score_breakdown"]["permission_score"] == 15

    def test_tc07_read_sms_plus_install_packages_critical(self):
        """TC-07: READ_SMS + INSTALL_PACKAGES = 75 pts → CRITICAL (OTP theft + silent APK install)."""
        manifest = """
            <uses-permission android:name="android.permission.READ_SMS"/>
            <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>
        """
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "CRITICAL"
        assert apk["score_breakdown"]["permission_score"] == 75

    def test_tc08_all_six_permissions_capped_at_100(self):
        """TC-08: All 6 dangerous permissions combined → capped at 100, CRITICAL."""
        manifest = """
            <uses-permission android:name="android.permission.READ_SMS"/>
            <uses-permission android:name="android.permission.RECEIVE_SMS"/>
            <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>
            <uses-permission android:name="android.permission.READ_CONTACTS"/>
            <uses-permission android:name="android.permission.RECORD_AUDIO"/>
            <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
        """
        result = audit(manifest=manifest)
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "CRITICAL"
        assert apk["total_score"] == 100  # capped
        assert len(apk["permission_findings"]) == 6


# ─── Phishing / Suspicious URL Patterns ─────────────────────────────────────

class TestSuspiciousURLPatterns:
    """Each URL pattern is tested individually and in combinations."""

    def test_tc09_direct_ip_address_evasion(self):
        """TC-09: Direct IP endpoint (http://45.33.32.156/api) — domain evasion tactic."""
        strings = '<string name="host">http://45.33.32.156/api/data</string>'
        result = audit(strings=strings)
        apk = result["apk_analysis"]
        url_urls = [f["url"] for f in apk["url_findings"]]
        assert any("45.33.32.156" in u for u in url_urls)
        assert apk["score_breakdown"]["url_score"] >= 20

    def test_tc10_high_risk_tld_dot_ru(self):
        """TC-10: .ru TLD frequently linked to phishing campaigns."""
        strings = '<string name="analytics">http://track.evil-analytics.ru/collect</string>'
        result = audit(strings=strings)
        apk = result["apk_analysis"]
        assert apk["score_breakdown"]["url_score"] >= 20
        url_urls = [f["url"] for f in apk["url_findings"]]
        assert any(".ru" in u for u in url_urls)

    def test_tc11_high_risk_tld_dot_xyz(self):
        """TC-11: .xyz TLD — known low-cost domain used in malware distribution."""
        strings = '<string name="cdn">http://malicious-cdn.xyz/payload</string>'
        result = audit(strings=strings)
        apk = result["apk_analysis"]
        assert apk["score_breakdown"]["url_score"] >= 20

    def test_tc12_high_risk_tld_dot_top(self):
        """TC-12: .top TLD — high-risk domain used in phishing kits."""
        strings = '<string name="api">https://fake-bank.top/login</string>'
        result = audit(strings=strings)
        apk = result["apk_analysis"]
        assert apk["score_breakdown"]["url_score"] >= 20

    def test_tc13_exfil_keyword_in_url(self):
        """TC-13: 'exfil' keyword in URL path — data exfiltration endpoint."""
        strings = '<string name="endpoint">http://c2.attacker.com/exfil/sms</string>'
        result = audit(strings=strings)
        apk = result["apk_analysis"]
        assert apk["score_breakdown"]["url_score"] >= 20
        url_urls = [f["url"] for f in apk["url_findings"]]
        assert any("exfil" in u for u in url_urls)

    def test_tc14_phish_keyword_in_url(self):
        """TC-14: 'phish' keyword in URL — explicit phishing infrastructure."""
        strings = '<string name="auth">http://update-service.com/phish/bank</string>'
        result = audit(strings=strings)
        apk = result["apk_analysis"]
        assert apk["score_breakdown"]["url_score"] >= 20

    def test_tc15_multiple_phishing_urls_warning(self):
        """TC-15: Two suspicious URLs (IP + .ru) = 40 pts → WARNING."""
        strings = """
            <string name="host">http://192.168.99.1/steal</string>
            <string name="report">http://report.spy.ru/upload</string>
        """
        result = audit(strings=strings)
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "WARNING"
        assert apk["score_breakdown"]["url_score"] >= 40


# ─── Combined Attack Scenarios ───────────────────────────────────────────────

class TestCombinedScenarios:
    def test_tc16_stalkerware_apk_critical(self):
        """TC-16: Stalkerware pattern — SMS read + fine location + .ru exfil URL → CRITICAL."""
        manifest = """
            <uses-permission android:name="android.permission.READ_SMS"/>
            <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
        """
        strings = '<string name="c2">http://tracker.spyware.ru/upload</string>'
        result = audit(manifest=manifest, strings=strings)
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "CRITICAL"
        # 35 (READ_SMS) + 15 (LOCATION) + 20 (.ru) = 70 → CRITICAL
        assert apk["total_score"] >= 70

    def test_tc17_banking_trojan_pattern(self):
        """TC-17: Banking trojan — INSTALL_PACKAGES + RECEIVE_SMS + direct IP exfil → CRITICAL."""
        manifest = """
            <uses-permission android:name="android.permission.INSTALL_PACKAGES"/>
            <uses-permission android:name="android.permission.RECEIVE_SMS"/>
        """
        strings = '<string name="drop">http://10.0.0.5/exfil/otp</string>'
        result = audit(manifest=manifest, strings=strings)
        apk = result["apk_analysis"]
        assert apk["threat_level"] == "CRITICAL"
        assert len(apk["permission_findings"]) == 2
        assert len(apk["url_findings"]) >= 2  # IP match + exfil keyword


# ─── PI (Personal Information) Detection ────────────────────────────────────

class TestPIDocumentScan:
    def test_tc18_rrn_detection_critical(self):
        """TC-18: Korean Resident Registration Number (RRN) triggers PI CRITICAL + encryption."""
        doc = "Name: Kim Tony, RRN: 950101-1234567, Address: Seoul"
        result = audit(document_text=doc)
        pi = result["pi_analysis"]
        assert pi["risk"] == "CRITICAL"
        assert "RSA-OAEP" in pi["encryption"]
        assert any("RRN" in d for d in pi["details"])

    def test_tc19_bank_account_detection(self):
        """TC-19: Bank account number (10–14 digits) detected in document."""
        doc = "Please transfer to account: 12345678901234"
        result = audit(document_text=doc)
        pi = result["pi_analysis"]
        assert pi["risk"] == "CRITICAL"
        assert any("Bank" in d for d in pi["details"])

    def test_tc20_clean_document_no_pi(self):
        """TC-20: Document with no PI patterns → SAFE, no encryption needed."""
        doc = "This is a general meeting note with no personal information."
        result = audit(document_text=doc)
        pi = result["pi_analysis"]
        assert pi["risk"] == "SAFE"
        assert pi["encryption"] == "None"
        assert pi["details"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
