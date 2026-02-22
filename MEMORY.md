# MEMORY (auto-updated)
Generated: Sun Feb 22 14:35:00 KST 2026

## Core Info
- 사용자: Andy (Telegram id: 5510621427, timezone: Asia/Seoul, 선호 언어: 한국어)
- 코딩 모델: claude-opus-4.5 #preference
- 호스트 OS: macOS (Darwin arm64) — systemd 불가, launchd 사용

## 보안 체계 (2026-02-22 구축) #decision
- SECURITY_POLICY.md: 4개 레이어 (인젝션 방어, 데이터 보호, 승인 게이트, 자동 체크)
- 자동 레닥션: poc/security/redact.py (아웃바운드 메시지에서 API 키/토큰 자동 마스킹)
- 자동 스케줄 (LaunchAgent 4개 설치됨):
  - 매일 03:30 코드 스캔 (scanner_v3.py)
  - 매주 월 04:00 게이트웨이 검증 (gateway_verify.py)
  - 매주 월 04:15 레포 사이즈 모니터 (repo_size_monitor.py)
  - 매월 1일 04:30 메모리 스캔 (memory_scan.py)
- 발견: gmail_30_summary.txt에 봇 토큰 노출(4건), inbound 세션에 OAuth secret 노출(1건) — 회전/삭제 권고

## PoC 현황
- CRM: poc/crm.db + FAISS, Gmail 24건, Flask API :5000
- 긴급 이메일: poc/scripts/urgent_simulate_and_extract.py, 시간대 게이트(평일 17-21, 주말 07-21)
- 비즈니스 분석: 3 전문가 스캐폴드, 데모 다이제스트 전송 완료
- 개인 RAG: 자동 게시 모드, poc/knowledge 스캐폴드
- 수동-승인(CMD: B모드) 정책 적용 중

## 교훈 #lesson
- macOS에서 systemd 사용 불가 → launchd 사용
- 보안 스캐너 실행 시 프로세스 세션 충돌 반복 → 경량 스크립트(flush stdout, 짧은 실행)로 해결
- 스캐너가 자기 리포트 파일을 재스캔하는 자기참조 문제 → SKIP_FILES에 추가

## Todos (#todo)
- credentials/ 파일 권한 600 설정
- gmail_30_summary.txt 내 노출 토큰 마스킹/삭제
- inbound 세션 OAuth secret 정리
- Fathom/Todoist API 토큰 대기
- Box token 대기
- Slack token 대기



# Previous MEMORY content
# MEMORY.md

이 파일은 Clawd의 장기 기억 저장소입니다. 중요한 결정, 선호도, 지속적으로 기억할 가치가 있는 사실들을 여기에 정리하세요.

예시 항목:
- 사용자 이름: Andy
- 선호 언어: 한국어
- Telegram user id: 5510621427
- 주요 프로젝트: Telegram-OpenClaw 통합, itinerary generation

작성 규칙:
- 날짜별로 짧게 정리하세요(요점 위주).
- 민감한 정보는 저장 금지(비밀번호, 토큰 등).
- 중요한 결정이나 장기 할당은 별도 태그로 표시하세요: #decision #preference

---

# Recent

- 2026-02-21: Remote Mouse 설치 및 권한 하드닝 작업 수행.
- 2026-02-21: Telegram bot tokens 및 google_oauth_client.json 처리 필요(백업 완료).
