import json
import re

class AIPIDetector:
    """Simulates AI-based PI detection (BERT/Sequence Labeling)"""
    def __init__(self):
        self.patterns = {
            "RRN": r"\d{6}-\d{7}",
            "CreditCard": r"\d{4}-\d{4}-\d{4}-\d{4}",
            "BankAccount": r"\d{10,14}"
        }

    def scan(self, text: str):
        results = []
        for pi_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                results.append({"type": pi_type, "count": len(matches), "risk": "HIGH"})
        return results

class SandboxPhishingAnalyzer:
    """Simulates Sandbox-based App Analysis"""
    def analyze_apk(self, apk_name: str, behavior_log: list):
        risk_score = 0
        findings = []
        
        # Suspicious Behaviors from Patent
        suspicious_actions = {
            "SMS_STEAL": 40,
            "NETWORK_TO_KNOWN_PHISHING_IP": 50,
            "HIDE_ICON": 20,
            "OVERLAY_ATTACK": 30
        }
        
        for action in behavior_log:
            if action in suspicious_actions:
                weight = suspicious_actions[action]
                risk_score += weight
                findings.append(f"Detected suspicious action: {action} (Weight: {weight})")
        
        threat_level = "SAFE"
        if risk_score > 70: threat_level = "CRITICAL"
        elif risk_score > 30: threat_level = "WARNING"
        
        return {
            "app": apk_name,
            "risk_score": risk_score,
            "threat_level": threat_level,
            "findings": findings
        }

if __name__ == "__main__":
    detector = AIPIDetector()
    doc_text = "Student name: Tony, RRN: 950101-1234567, Bank: 123456789012"
    print("--- PI Detection Results ---")
    print(json.dumps(detector.scan(doc_text), indent=2))
    
    analyzer = SandboxPhishingAnalyzer()
    mock_behavior = ["SMS_STEAL", "NETWORK_TO_KNOWN_PHISHING_IP"]
    print("\n--- Sandbox Phishing Analysis ---")
    print(json.dumps(analyzer.analyze_apk("suspicious_reward.apk", mock_behavior), indent=2))
