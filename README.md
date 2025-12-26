# 🤖 AI 기반 네이버 블로그 자동 콘텐츠 생성 및 업로드 시스템

**완전 자동화된 고품질 블로그 콘텐츠 생성 시스템** ✅ 구현 완료!

암호화폐 뉴스를 실시간으로 수집하여 AI(Claude 4.5, Gemini 3 Pro, Perplexity)를 통해 인간보다 더 인간적인 블로그 포스팅을 생성하고, Playwright를 이용해 네이버 블로그에 자동으로 업로드합니다.

---

## 🎯 주요 기능

### 🔬 5개의 전문화된 AI 에이전트

1. **Research Orchestrator** - Perplexity + RSS 피드로 실시간 시장 인사이트 수집
2. **Content Synthesizer** - Claude 4.5 Sonnet으로 페르소나 기반 고품질 글쓰기
3. **Visual Designer** - Gemini 3 Pro로 컨텍스트 기반 이미지 생성
4. **QA Agent** - AI 간 교차 검증 및 품질 보증 (70점 미만 자동 재생성)
5. **Upload Orchestrator** - Playwright 스텔스 모드로 봇 탐지 우회

### 🛡️ 엔터프라이즈급 보안

- ✅ 시스템 키체인 통합 (macOS Keychain, Windows DPAPI)
- ✅ AES-256 암호화 (환경 변수, 세션 파일)
- ✅ Rate Limiting (API 호출 제한, 계정 보호)
- ✅ 로그 마스킹 (민감 정보 자동 제거)

### 🎭 Human-like 자동화

- ✅ 베지어 곡선 기반 마우스 이동
- ✅ 개인별 타이핑 리듬 시뮬레이션
- ✅ 자연스러운 스크롤 및 휴식 시간

---

## 🚀 빠른 시작

### 1️⃣ 자격증명 설정

```bash
# 대화형 설정 실행
python security/credential_manager.py
```

### 2️⃣ 실행

```bash
# 테스트 모드 (업로드 안 함)
python main.py --naver-id YOUR_ID --test --once

# 실제 운영
python main.py --naver-id YOUR_ID --once
```

---

## 📂 문서 안내

- **[FINAL_MASTER_PLAN.md](FINAL_MASTER_PLAN.md)** - 전체 로드맵 및 아키텍처 ⭐
- **[QUICK_START.md](QUICK_START.md)** - 단계별 설치 가이드
- **[SECURITY_ALERT.md](SECURITY_ALERT.md)** - 보안 주의사항 (필독!)
- [CONTENT_STRATEGY.md](CONTENT_STRATEGY.md) - 콘텐츠 전략
- [TECHNICAL_SPECS.md](TECHNICAL_SPECS.md) - 기술 사양

---

## ⚠️ 법적 고지

본 시스템은 **교육 및 연구 목적**으로 설계되었습니다.
네이버 이용약관을 준수해야 하며, 자동화로 인한 계정 정지 리스크는 사용자에게 있습니다.

**[SECURITY_ALERT.md](SECURITY_ALERT.md)를 반드시 읽어주세요!**

---

**Happy Automating! 🚀**
