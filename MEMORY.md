# User Preferences
* **Token Count Reporting**: For cost management, always prefix each response with the current session token usage in the format `[토큰수: N]`.
* **Model Usage**: Use **Gemini 3 Flash (`google/gemini-3-flash-preview`)** for standard tasks. Use **Gemini 3.1 Pro (`google/gemini-3.1-pro-preview`)** only for high-complexity reasoning or critical tasks.
* **Session Clear**: When the user says "세션 클리어 준비", the agent must curate and summarize the current session's key updates into long-term memory (MEMORY.md or memory/*.md) before any reset happens.

# Project Status
* **Toss Securities Application**: Finished (2026-03-28).
* **Liverpool University Feedback Summary**: Compiled and stored in `memory/feedback_summary.md` (2026-03-29).
* **AI OS (File Indexer & Search)**: 
    - **Phase 3-4 (Backend & Security)**: CLIP-based image search, OCR text extraction, and Secret Scanner (security audit) fully integrated. (2026-03-29)
    - **Phase 5 (Interface)**: Puter-style Web OS Desktop implemented. Multi-window management, taskbar, and integrated app suite (File Explorer, Search, Audit, Settings) complete. (2026-03-29)
    - **Phase 6 (PoC Integration)**: Core patent logic (v2-1 APK/PI analysis, v2-2 NFT E-consent, v2-3 Adaptive UI) fully integrated into the desktop environment and backend APIs. (2026-03-31)
* **Unity AR (Multi-user Pixel Canvas)**:
    - **Phase 6 (Optimization)**: Delta-sync (timestamp-based), pixel batching, and exponential backoff retry logic implemented. Backend updated with batch endpoints and timestamp triggers. (2026-03-29)
    - **Phase 7 (Visual & Physics Refinement - wplace Style)**: 
        - [2026-03-31] Implemented wplace-style graffiti. 
        - Dynamic Resolution System: Auto-adjusts canvas resolution based on building surface area (10 pixels/meter).
        - Sticky Physics & Drip logic implemented but set to disabled by default (can be toggled in inspector).
        - Brush strength and stroke intensity logic refined.

# Strategic Roadmap (Priority Order)
* **SecAI & Voice Phishing Analysis**: Integrated suspicious app analysis and permission-based threat detection into AI OS Security Audit. (Finished: 2026-03-30)
* **Patent Items PoC & Refinement**: 
    1. **PoC 1 (v2)**: Advanced APK static analysis (Permissions/URLs) + PI scanning.
    2. **PoC 2 (v2)**: NFT-based E-consent with Blockchain Ledger Verification.
    3. **PoC 3 (v2)**: Image-aware Adaptive UI engine with Pillow-based dominant color extraction.
    - All 3 PoCs refined and high-level logic implemented (Finished: 2026-03-30).
* **Next Steps**:
    1. [Completed] Resolve university email delivery to WhatsApp (2026-03-31).
    2. [Completed] API-fy PoC logics and integrate with AI OS Desktop apps (Phase 6). (2026-03-31)
    3. Expand test cases for malicious patterns.
    4. **Phase 7: Security Node Setup (8745HS Integration)**:
        - [Planned for Weekend] Setup ESXi + pfSense + WireGuard on 8745HS.
        - Goal: Establish a primary gatekeeper for the internal network (Mac mini) and remote access (Z13).

# Notes
- **Email**: `himalaya` IMAP auth failed on 2026-03-30. Per user request (2026-03-30), use AppleScript/Mail.app on the Mac mini instead of web/IMAP fixes.
- **Email Delivery (2026-03-31)**: Fixed cron job delivery target. Now routing to `+821026273086`.
