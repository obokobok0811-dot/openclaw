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
- 긴급 이메일: poc/urgent/ (TF-IDF+LR 분류기 F1=0.865, 30분 폴링, 시간대 게이트, 피드백 재학습)
- 비즈니스 분석: 8 전문가 (BaseExpert 상속) + Synthesizer, poc/experts/
- 개인 RAG: poc/knowledge/ (수집→파싱→NER→임베딩→검색, auto-post 모드, Flask API)
- 수동-승인(CMD: B모드) 정책 적용 중

## 교훈 #lesson
- macOS에서 systemd 사용 불가 → launchd 사용
- 보안 스캐너 실행 시 프로세스 세션 충돌 반복 → 경량 스크립트(flush stdout, 짧은 실행)로 해결
- 스캐너가 자기 리포트 파일을 재스캔하는 자기참조 문제 → SKIP_FILES에 추가

## 자동화 서비스 (LaunchAgent 9개 활성) #infra
- security-scanner: 매일 03:30
- gateway-verify: 매주 월 04:00
- repo-size-monitor: 매주 월 04:15
- memory-scan: 매월 1일 04:30
- db-backup: 매시간 (poc/backup/backup_databases.py)
- git-sync: 매시간 (scripts/git/auto_sync.py, pre-commit hook 포함)
- usage-parser: 매시간 (poc/tracking/gateway_parser.py → usage.jsonl)
- usage-report: 매일 23:55 (poc/tracking/daily_report.py → Telegram)
- urgent-email: 30분 간격 (poc/urgent/poller.py → Gmail 스캔 → ML 분류 → 시간대 게이트 → Telegram)

## Git 설정 #infra
- user: Clawd <clawd@openclaw.ai>
- remote 미설정 (로컬 커밋+태그만)
- pre-commit hook: 민감 데이터 차단 (API키, 봇토큰, JWT, .key/.pem)

## 사용량 트래커 #infra
- poc/tracking/tracker.py: 19개 모델 가격표, 4개 provider 자동 감지
- gateway_parser.py: 게이트웨이 로그에서 호출 자동 수집 (duration 기반 토큰 추정, ±20%)
- 2026-02-22 첫 수집: 122회, $10.13 (opus-4.6 10회 $6.08 / gpt-5-mini 112회 $4.05)

## Todos (#todo)
- ~~credentials/ 파일 권한 600 설정~~ ✅ 2026-02-22
- ~~gmail_30.jsonl 내 노출 토큰 마스킹~~ ✅ 2026-02-22 (plain + base64 전량 레닥션)
- ~~inbound 세션 OAuth secret 정리~~ ✅ 2026-02-22 (디렉토리 삭제)
- git remote 설정 (사용자 제공 대기)
- Fathom/Todoist API 토큰 대기
- Box token 대기
- Slack token 대기
- gdrive_token.json 대기 (백업 Drive 업로드용)



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
