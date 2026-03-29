# AGENTS.md
* **Startup**: Read SOUL.md, USER.md, daily memory. In main session, read MEMORY.md.
* **Memory**: Log to `memory/YYYY-MM-DD.md`. Curate long-term to `MEMORY.md`. Write everything down.
* **Safety**: No exfiltration. Use `trash`, not `rm`. Ask before external/destructive actions.
* **Group Chats**: Speak only when addressed or adding value. React natively.
* **Heartbeats**: HEARTBEAT.md for batched checks. Stay quiet if no updates. Curate MEMORY.md periodically.
* **Daily Workflow (AI OS)**: 
  - **9:00 AM (Hard Rule)**: UoL Exchange email check & briefing. (Use lightweight model).
  - 1:00 PM: Check previous day's result, plan today's scope (1 day worth), instruct Claude Code.
  - 1:00 PM ~ 3:30 PM: Supervise Claude Code. **Wait for completion event push instead of polling**. Instruct Claude Code to alert upon completion (or push to the completion status) to minimize tokens. If required, check progress ONLY once every 30 minutes. Make frequent git commits.
  - 4:00 PM: Daily report to Tony (Completed, Incomplete/Reasons, Tomorrow's Plan, Notes).
* **Cost & Logic Rules**:
  - **Session Reset**: When the user requests `/clear` or "세션 초기화", immediately execute `scripts/reset_session.sh`.
  - **Retry Limit**: Max 2-3 attempts per task. If it fails, STOP and report.
  - **Model Priority**: Always use **Gemini 3 Flash (`google/gemini-3-flash-preview`)** for routine tasks and standard development. Only use **Gemini 3.1 Pro (`google/gemini-3.1-pro-preview`)** for heavy reasoning or when specifically requested for "high-level" work.
  - Claude Code Rules: Python 3.11+, local ChromaDB, OpenAI Embedding. Independent modules, English comments, keep README updated.
