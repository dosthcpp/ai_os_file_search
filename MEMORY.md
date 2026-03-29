
# User Preferences
* **Token Count Reporting**: For cost management, always prefix each response with the current session token usage in the format `[토큰수: N]`.
* **Model Usage**: Use **Gemini 3 Flash (`google/gemini-3-flash-preview`)** for standard tasks. Use **Gemini 3.1 Pro (`google/gemini-3.1-pro-preview`)** only for high-complexity reasoning or critical tasks.

# Project Status
* **Toss Securities Application**: Finished (2026-03-28).
* **Liverpool University Feedback Summary**: Compiled and stored in `memory/feedback_summary.md` (2026-03-29).
* **AI OS (File Indexer & Search)**: 
    - **Phase 3-4 (Backend & Security)**: CLIP-based image search, OCR text extraction, and Secret Scanner (security audit) fully integrated. (2026-03-29)
    - **Phase 5 (Interface)**: Puter-style Web OS Desktop implemented. Multi-window management, taskbar, and integrated app suite (File Explorer, Search, Audit, Settings) complete. (2026-03-29)
* **Unity AR (Multi-user Pixel Canvas)**:
    - **Phase 6 (Optimization)**: Delta-sync (timestamp-based), pixel batching, and exponential backoff retry logic implemented. Backend updated with batch endpoints and timestamp triggers. (2026-03-29)
* **Deployment**: Final testing and push to production (main) branches complete. (2026-03-29)

# Strategic Roadmap (Priority Order)
1. **SecAI & Voice Phishing Analysis**: Integrate suspicious app analysis into AI OS Security Audit (Sandbox approach). (Target: 2026-03-30)
2. **Patent Items PoC**: Write PoC for patent-related items after deployment.
3. **PoC Refinement**: High-level enhancement of existing PoCs.
4. **Branch Strategy**: Use separate branches for `secure` and `patent` items.
