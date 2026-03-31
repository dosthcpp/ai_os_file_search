import json
import re
from typing import Dict, Any, List

class SecAIAnalyzer:
    """
    SecAIAnalyzer: Analyzes file content for security threats and voice phishing patterns.
    """
    def __init__(self):
        self.risk_score = 0
        self.findings = []
        
        # Rule-based Detection Engine: Suspicious API patterns
        self.suspicious_apis = {
            "sendTextMessage": 20,
            "callPhoneNumber": 20,
            "requestLocationUpdates": 15,
            "queryContacts": 10,
            "recordAudio": 15,
            # Voice Phishing specific indicators
            "installPackage": 25,
            "deletePackage": 25,
            "getRunningTasks": 15,
            "getRecentTasks": 15,
            "killBackgroundProcesses": 15
        }
        
        # Sensitive Permissions mapping
        self.sensitive_permissions = [
            "android.permission.SEND_SMS",
            "android.permission.READ_CONTACTS",
            "android.permission.RECORD_AUDIO",
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.RECEIVE_SMS",
            "android.permission.READ_SMS",
            "android.permission.CALL_PHONE",
            "android.permission.PROCESS_OUTGOING_CALLS",
            "android.permission.SYSTEM_ALERT_WINDOW"
        ]

    def analyze(self, content: str) -> Dict[str, Any]:
        """
        Perform a full analysis on the provided content.
        """
        self.risk_score = 0
        self.findings = []
        
        self._scan_static_patterns(content)
        self._trace_permissions(content)
        
        threat_level = self.get_threat_level()
        
        report = {
            "threat_level": threat_level,
            "risk_score": self.risk_score,
            "findings": self.findings[:5] # Limit findings for metadata
        }
        
        if threat_level in ["CRITICAL", "WARNING"]:
            report["security_audit_alert"] = f"SecAI detected {threat_level} threat level (Score: {self.risk_score})"
            
        return report

    def _scan_static_patterns(self, content: str):
        """Analyze content for suspicious API calls and calculate risk."""
        for api, weight in self.suspicious_apis.items():
            if re.search(api, content):
                self.risk_score += weight
                self.findings.append(f"Suspicious API call detected: {api}")

    def _trace_permissions(self, content: str):
        """Analyze sensitive permissions in content (e.g., manifest or code)."""
        for perm in self.sensitive_permissions:
            if perm in content:
                self.risk_score += 10
                self.findings.append(f"Sensitive permission requested: {perm}")

    def get_threat_level(self) -> str:
        if self.risk_score >= 80: return "CRITICAL"
        if self.risk_score >= 35: return "WARNING"
        return "SAFE"

    @staticmethod
    def get_summary_metadata(text: str) -> Dict[str, Any]:
        """
        Static helper to run analysis and return metadata-ready dictionary.
        """
        analyzer = SecAIAnalyzer()
        return analyzer.analyze(text)
