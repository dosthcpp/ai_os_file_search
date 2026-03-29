import re
from typing import List, Dict

# Common patterns for secrets (non-exhaustive but good for PoC)
SECRET_PATTERNS = {
    "OpenAI API Key": r"sk-[a-zA-Z0-9]{48}",
    "GitHub Personal Access Token": r"ghp_[a-zA-Z0-9]{36}",
    "AWS Access Key ID": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Access Key": r"secret_access_key\s*[:=]\s*['\"]?[a-zA-Z0-9/+=]{40}['\"]?",
    "Slack Webhook URL": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",
    "Generic Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
    "Google API Key": r"AIza[0-9A-Za-z-_]{35}",
    "Heroku API Key": r"[hH][eE][rR][oO][kK][uU].*[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
}

class SecretScanner:
    """
    Scans text content for potential secrets and sensitive information.
    """

    @staticmethod
    def scan(text: str) -> List[Dict[str, str]]:
        """
        Scan the provided text against known secret patterns.
        Returns a list of dictionaries containing the type and the found match (masked).
        """
        findings = []
        for secret_type, pattern in SECRET_PATTERNS.items():
            matches = re.findall(pattern, text)
            for match in matches:
                # Mask the secret for safety in logs/metadata
                if len(match) > 8:
                    masked = match[:4] + "..." + match[-4:]
                else:
                    masked = "****"
                findings.append({
                    "type": secret_type,
                    "match": masked
                })
        return findings

    @staticmethod
    def get_summary_metadata(text: str) -> Dict[str, any]:
        """
        Returns a summary dict suitable for ChromaDB metadata.
        """
        findings = SecretScanner.scan(text)
        if not findings:
            return {"has_secrets": False, "secrets_count": 0}
        
        # Join types for a quick overview string
        types = list(set(f["type"] for f in findings))
        return {
            "has_secrets": True,
            "secrets_count": len(findings),
            "secrets_types": ", ".join(types[:3]) + ("..." if len(types) > 3 else "")
        }
