import unittest
import sys
from pathlib import Path

# Add the packages/file-indexer to sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "packages" / "file-indexer"))

from sec_ai_analyzer import SecAIAnalyzer

class TestSecAIAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = SecAIAnalyzer()

    def test_safe_content(self):
        content = "This is a normal file with no suspicious APIs."
        result = self.analyzer.analyze(content)
        self.assertEqual(result["threat_level"], "SAFE")
        self.assertEqual(result["risk_score"], 0)
        self.assertNotIn("security_audit_alert", result)

    def test_warning_content(self):
        # Multiple suspicious APIs/permissions to trigger WARNING
        content = """
        void myFunc() {
            sendTextMessage("123", "Hello");
            requestLocationUpdates();
        }
        """
        result = self.analyzer.analyze(content)
        self.assertEqual(result["threat_level"], "WARNING")
        self.assertGreaterEqual(result["risk_score"], 35)
        self.assertIn("security_audit_alert", result)

    def test_critical_content(self):
        # Many suspicious APIs and permissions to trigger CRITICAL
        content = """
        void main() {
            sendTextMessage("112", "Urgent");
            callPhoneNumber("112");
            installPackage("evil.apk");
            deletePackage("security.apk");
            recordAudio();
        }
        android.permission.SEND_SMS
        android.permission.RECEIVE_SMS
        android.permission.SYSTEM_ALERT_WINDOW
        """
        result = self.analyzer.analyze(content)
        self.assertEqual(result["threat_level"], "CRITICAL")
        self.assertGreaterEqual(result["risk_score"], 100)
        self.assertIn("security_audit_alert", result)

    def test_static_metadata_helper(self):
        content = "sendTextMessage"
        meta = SecAIAnalyzer.get_summary_metadata(content)
        self.assertEqual(meta["risk_score"], 20)
        self.assertEqual(meta["threat_level"], "SAFE")

if __name__ == "__main__":
    unittest.main()
