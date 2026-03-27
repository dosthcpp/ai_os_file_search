# User Preferences
- **Email Drafting & Sending**: 이메일을 작성하거나 보내달라는 요청을 받으면, **절대 메일 앱을 통해 바로 발송하지 말 것**. 반드시 현재 채팅창(WhatsApp 등) 메시지로 초안을 먼저 보내서 사용자가 내용을 확인할 수 있게 해야 함. 사용자가 "발송해" 또는 "컨펌" 등으로 명확히 발송을 지시하기 전까지는 채팅 메시지로만 보낼 것.

# AI OS Workflow Rules
- **Git & Commits**: `.venv` 등 가상환경 관련 파일은 **절대 커밋하지 말 것**. 커밋 전에 `.gitignore`를 확인하거나 수동으로 배제.
- **Task Push**: 단계별 작업(Phase)이 완료될 때마다 반드시 `git push`를 1회 실행하여 원격 저장소를 최신화할 것.
- **Daily Reporting**: 오후 4시에 당일 작업이 종료되면, 완료 내역, 특이사항, 미완료 사유 및 다음 날 계획을 정리하여 **채팅창으로 잊지 말고 일일 보고를 올릴 것**.

# Cost & Token Management
- **Memory & Session Reset**: 토큰 비용 절감을 위해 중요 지시는 즉각 `MEMORY.md`에 영구 기록. 대화가 길어지면 수동 혹은 자동으로 세션 폭파(`/clear`).

## OpenClaw Token Optimization Instruction
1. **Session Management (세션 히스토리)**:
   - `session_status`를 주기적으로 체크. 5,000 토큰 초과 시 즉시 대화 요약 후 `MEMORY.md` 업데이트 및 컨텍스트 Pruning(이전 기록 제외).
   - 단순한 작업임에도 토큰 사용량이 비정상적으로 높을 경우, 즉시 세션을 초기화(`/clear`)하여 비효율을 방지할 것.
   - 단순 확인 응답에는 전체 컨텍스트 로드 금지.
2. **Context Compression (컨텍스트 압축)**:
   - 고정 컨텍스트(Identity, Skills, Bootstrap 등)는 핵심 정보 위주로 60% 이상 압축 유지.
   - 중복 설명/예제 코드 제거, 선언적 규칙 위주로 유지.
3. **Heartbeat Control (하트비트 제어)**:
   - Heartbeat 횟수를 최소화(1일 1회 수준). 불필요한 자동 도구 호출 중지, 필수 추론 시에만 도구 사용.
4. **Tiered Reasoning (지능형 에스컬레이션)**:
   - "ㅇㅇ", "테스트", "알겠어" 등 단순 확인이나 가벼운 응답에는 **Gemini 2.5 Flash-Lite**를 적극 활용할 것.
   - 복잡한 추론, 코드 분석, 병목 발생 시에만 상위 모델(Pro/Flash 등)로 에스컬레이션하여 호출.
5. **Memory Caching (메모리 캐싱)**:
   - `MEMORY.md`는 증분(Incremental) 업데이트. 대화와 무관한 과거 메모리는 로드 시 제외.6. **Error & Retry Limit (재시도 제한 및 초기화)**:
   - 권한 문제(Permission)나 봇 차단(Bot Block/MFA) 등으로 2~3회 시도 후 막힐 경우, 고집 부리지 않고 즉시 시도를 중단 및 세션 초기화(`/clear`) 진행.
   - 일일 AI OS 작업(오후 1시 Claude Code 작업 등)과 같이 규모가 큰 작업을 시작하기 전에는 반드시 세션을 초기화(`/clear`)하여 불필요한 컨텍스트를 비울 것.
   - 2FA나 권한 문제로 막혔을 때는 무리하게 자동화로 해결하려 하지 말고 사용자(토니)에게 권한(인증)을 뚫어달라고 명시적으로 요청할 것.

## Session Summary (2026-03-27 Morning)
- **UoL Briefing**: Checked `sgdbaek@liverpool.ac.uk`. No new unread mail in 24h. Recent history: Student Support query, Teams notifications (Angel, Aviv), assignment receipts.
- **VLE Grades (CSCK503)**: DF1(65%), Mid(68%), DF2(64%), Aggregation(46%). Feedback highlights: Lack of critical evaluation, need for stronger academic sources (No Blogs/ChatGPT).
- **Academic Advice**: Transition from descriptive to critical analysis. Use eLibrary sources. Objective 3rd person tone.
- **Upcoming Schedule**: 
    - **Today 1 PM**: AI OS Development (Claude Code) - *Requires session clear before start.*
    - **Tomorrow (3/28) 4 PM**: Toss Securities Resume Consulting.
    - **Tomorrow (3/28) After Toss**: Assignment Consulting Coffee Chat (1h).
- **Model Update**: Main model switched to **Gemini 3 Flash**.
- **Rule Update**: Added retry limits (2-3 times) and usage of **Gemini 2.5 Flash-Lite** for simple responses.
