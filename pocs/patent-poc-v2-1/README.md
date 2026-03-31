# Patent PoC 1 — AI E-Consent System with Static APK Phishing Detection

## Invention Title
AI-Powered E-consent Auto-Detection, Encryption, Biometric Signature & Sandbox-Based Phishing Detection System

---

## Overview
This PoC simulates the "Single-Pass" pipeline where a document is simultaneously indexed for search and audited for security risks. The APK analysis component performs **static** inspection of a mock Android manifest and string-resource file to detect dangerous permissions and suspicious embedded URLs, without requiring runtime execution.

---

## Key Modules

| Class / Component | Role |
|---|---|
| `AIOS_UnifiedAudit` | Orchestrator — runs document PI scan and APK analysis |
| `APKStaticAnalyzer` | Scans APK manifest for dangerous permissions and string resources for suspicious URLs |

---

## APK Static Analysis Logic

### Permission Scanner
Matches `android.permission.*` declarations in the manifest against a weighted table of dangerous permissions:

| Permission | Risk Score | Reason |
|---|---|---|
| `INSTALL_PACKAGES` | 40 | Silent APK installation vector |
| `READ_SMS` | 35 | OTP/2FA theft |
| `RECORD_AUDIO` | 30 | Microphone stalkerware |
| `RECEIVE_SMS` | 25 | Real-time SMS interception |
| `READ_CONTACTS` | 20 | Contact list exfiltration |
| `ACCESS_FINE_LOCATION` | 15 | Precise GPS tracking |

### URL Pattern Scanner
Inspects embedded strings for three heuristic patterns:
1. **Direct IP endpoints** — `http://45.x.x.x/...` (no domain, evasion tactic)
2. **High-risk TLDs** — `.ru`, `.biz`, `.xyz`, `.top`
3. **Suspicious keywords** — `exfil`, `track`, `collect`, `evil`, `phish`

### Threat Score Breakdown
```
total_score = permission_score + url_score  (capped at 100)

CRITICAL  ≥ 70
WARNING   ≥ 40
SAFE      < 40
```

---

## Usage
```bash
python poc_main.py
```

### Sample Output
```json
{
  "threat_level": "CRITICAL",
  "total_score": 100,
  "score_breakdown": {
    "permission_score": 100,
    "url_score": 60
  },
  "permission_findings": [...],
  "url_findings": [...],
  "summary": "3 dangerous permission(s) and 3 suspicious URL(s) detected."
}
```

---

## Dependencies
- Python 3.11+ (stdlib only — `re`, `json`)
