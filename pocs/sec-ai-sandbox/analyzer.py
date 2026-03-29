import json
import re

class SecAIAnalyzer:
    def __init__(self, app_path: str):
        self.app_path = app_path
        self.risk_score = 0
        self.findings = []
        
        # Rule-based Detection Engine: Suspicious API patterns
        self.suspicious_apis = {
            "sendTextMessage": 20,
            "callPhoneNumber": 20,
            "requestLocationUpdates": 15,
            "queryContacts": 10,
            "recordAudio": 15
        }
        
        # Sensitive Permissions mapping
        self.sensitive_permissions = [
            "android.permission.SEND_SMS",
            "android.permission.READ_CONTACTS",
            "android.permission.RECORD_AUDIO",
            "android.permission.ACCESS_FINE_LOCATION"
        ]

    def scan_static_patterns(self, content: str):
        """Analyze content for suspicious API calls and calculate risk."""
        for api, weight in self.suspicious_apis.items():
            if re.search(api, content):
                self.risk_score += weight
                self.findings.append(f"Suspicious API call detected: {api}")

    def trace_data_flows(self, manifest_content: str):
        """Analyze sensitive permissions in manifest file."""
        for perm in self.sensitive_permissions:
            if perm in manifest_content:
                self.risk_score += 10
                self.findings.append(f"Sensitive permission requested: {perm}")

    def generate_report(self):
        return {
            "app_name": self.app_path,
            "threat_level": self.get_threat_level(),
            "risk_score": self.risk_score,
            "findings": self.findings
        }

    def get_threat_level(self):
        if self.risk_score > 80: return "CRITICAL"
        if self.risk_score > 40: return "WARNING"
        return "SAFE"

if __name__ == "__main__":
    # Mock analysis simulation
    analyzer = SecAIAnalyzer("mock_malware.apk")
    
    # Simulating static analysis of code and manifest
    analyzer.scan_static_patterns("System.callPhoneNumber('123456');")
    analyzer.trace_data_flows("android.permission.SEND_SMS")
    
    print(json.dumps(analyzer.generate_report(), indent=2))
