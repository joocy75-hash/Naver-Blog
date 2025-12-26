# 상세 구현 작업 계획서 (Granular Task List - Ultimate Edition)

본 문서는 `IMPLEMENTATION_PLAN.md`의 Ultimate 전략을 실행하기 위한 세부 태스크 리스트입니다.

---

## 1. 환경 구축 및 API 통합 (Phase 1)

- [ ] **가상환경 및 라이브러리**:
  - `openai` (Perplexity용), `anthropic`, `google-generativeai`, `playwright-stealth` 설치.
- [ ] **API 연동 테스트**:
  - [ ] Perplexity: 실시간 뉴스 검색 쿼리 테스트.
  - [ ] Claude: 페르소나 기반 텍스트 생성 테스트.
  - [ ] Gemini: 이미지 생성 및 분석 테스트.
- [ ] **MCP 설정**: `sequential-thinking`을 이용한 파이프라인 로직 설계.

## 2. 지능형 검색 및 콘텐츠 엔진 (Phase 2)

- [ ] **Perplexity Researcher**:
  - [ ] 시장 핫 이슈 추출을 위한 시스템 프롬프트 설계.
  - [ ] 검색 결과 파싱 및 데이터 구조화.
- [ ] **Claude Persona Writer**:
  - [ ] "일반 회원 리뷰" 페르소나 고도화.
  - [ ] Perplexity 데이터를 본문에 녹여내는 컨텍스트 주입 로직.
- [ ] **Gemini Visual Designer**:
  - [ ] 본문 기반 이미지 프롬프트 생성기 개발.
  - [ ] Pillow를 이용한 수익률/차트 데이터 이미지 합성 모듈.

## 3. Stealth 업로드 시스템 (Phase 3)

- [ ] **Playwright Stealth**:
  - [ ] 브라우저 핑거프린팅 우회 및 User-Agent 관리.
  - [ ] `storage_state.json` 기반 세션 자동 복구 로직.
- [ ] **Smart Editor ONE 자동화**:
  - [ ] 클립보드 방식의 본문 삽입 모듈.
  - [ ] 이미지 업로드 및 본문 내 최적 위치 삽입 로직.
  - [ ] 태그, 발행 옵션 자동 설정.

## 4. 데이터베이스 및 스케줄링 (Phase 4)

- [ ] **DB 스키마 (PostgreSQL/SQLite)**:
  - [ ] `News`, `Posts`, `Accounts`, `Analytics` 테이블 생성.
- [ ] **Orchestrator 개발**:
  - [ ] 검색 -> 생성 -> 업로드 전 과정을 제어하는 `main.py` 작성.
  - [ ] 에러 발생 시 재시도 및 로그 기록 로직.
- [ ] **스케줄러**: APScheduler를 이용한 불규칙한 시간대 포스팅 예약.

## 5. 고도화 및 모니터링 (Phase 5)

- [ ] **성과 분석**: 포스팅 후 조회수/댓글 수 트래킹 (추후 확장).
- [ ] **알림 시스템**: 텔레그램 봇을 통한 실시간 작업 현황 보고.
- [ ] **콘텐츠 믹스**: 뉴스 외에 'AI 자동매매 가이드' 등 정보성 글 자동 생성 추가.

---

## 💡 Ultimate 체크리스트

- [ ] Perplexity가 가져온 정보가 최신이며 정확한가?
- [ ] Claude의 말투가 광고가 아닌 '진짜 후기'처럼 느껴지는가?
- [ ] Gemini가 생성한 이미지가 블로그 주제와 일치하는가?
- [ ] Playwright가 네이버의 봇 탐지 시스템을 완벽히 우회하는가?
