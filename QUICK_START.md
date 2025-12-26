# 🚀 빠른 시작 가이드

## 1단계: 보안 설정 (필수!)

### ⚠️ 먼저 읽어주세요
**[SECURITY_ALERT.md](SECURITY_ALERT.md)** 파일을 반드시 읽고 API 키를 재발급하세요!

### 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# 에디터로 .env 파일 열어서 실제 값 입력
# 절대로 .env 파일을 Git에 커밋하지 마세요!
```

---

## 2단계: 의존성 설치

### Python 패키지
```bash
# 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### Node.js (MCP 서버용)
```bash
# Homebrew로 Node.js 설치 (macOS)
brew install node

# 또는 공식 사이트에서 다운로드
# https://nodejs.org/

# MCP 서버 전역 설치
npm install -g @modelcontextprotocol/server-sequential-thinking
npm install -g @modelcontextprotocol/server-brave-search
npm install -g @modelcontextprotocol/server-memory
npm install -g @modelcontextprotocol/server-filesystem
```

---

## 3단계: 데이터베이스 초기화

```bash
# 디렉토리 생성
mkdir -p data/logs data/images data/sessions secrets

# SQLite 사용 시 (기본)
# DATABASE_URL=sqlite:///./data/blog_bot.db 확인

# PostgreSQL 사용 시 (프로덕션 권장)
# 1. PostgreSQL 설치
brew install postgresql@15
brew services start postgresql@15

# 2. 데이터베이스 생성
createdb blogbot

# 3. .env에서 DATABASE_URL 수정
# DATABASE_URL=postgresql://localhost:5432/blogbot
```

---

## 4단계: 보안 암호화 설정

```bash
# 암호화 키 생성 및 자격증명 저장
python3 << 'EOF'
import keyring
import os
from cryptography.fernet import Fernet

# 1. 암호화 키 생성
key = Fernet.generate_key()
os.makedirs('secrets', exist_ok=True)
with open('secrets/encryption.key', 'wb') as f:
    f.write(key)
print("✅ 암호화 키 생성 완료")

# 2. 네이버 계정을 키체인에 저장
naver_id = input("네이버 ID: ")
naver_pw = input("네이버 비밀번호: ")
keyring.set_password("naver_blog", naver_id, naver_pw)
print("✅ 네이버 계정 키체인 저장 완료")

# 3. API 키들도 키체인에 저장
anthropic_key = input("Anthropic API Key: ")
keyring.set_password("api_keys", "anthropic", anthropic_key)

google_key = input("Google API Key: ")
keyring.set_password("api_keys", "google", google_key)

perplexity_key = input("Perplexity API Key: ")
keyring.set_password("api_keys", "perplexity", perplexity_key)

print("✅ 모든 API 키 저장 완료!")
print("\n이제 .env 파일에서 실제 값을 삭제하고 키체인에서 불러오도록 설정하세요.")
EOF
```

---

## 5단계: 테스트 실행

### Research Agent 테스트
```bash
python3 << 'EOF'
import asyncio
from agents.research_agent import ResearchAgent

async def test():
    agent = ResearchAgent()
    result = await agent.get_trending_topic()
    print(result)

asyncio.run(test())
EOF
```

### Content Agent 테스트
```bash
python3 << 'EOF'
from agents.content_agent import ContentAgent

agent = ContentAgent()
content = agent.generate_post(
    topic="비트코인 급등",
    research_data={"summary": "테스트 데이터"}
)
print(content)
EOF
```

---

## 6단계: 전체 파이프라인 실행

### 단일 포스트 생성 (테스트 모드)
```bash
# TEST_MODE=True로 설정하면 실제 업로드 안 함
python main.py --test
```

### 실제 운영 시작
```bash
# 스케줄러 시작 (하루 3회 자동 포스팅)
python main.py --daemon

# 또는 단일 실행
python main.py --once
```

---

## 📋 체크리스트

구현 전 필수 확인사항:

### 보안
- [ ] `.env` 파일에 실제 API 키 입력 (Git 커밋 절대 금지)
- [ ] `.env.example`에는 템플릿만 있는지 확인
- [ ] `.gitignore`에 `.env` 포함 확인
- [ ] 키체인에 자격증명 저장 완료
- [ ] 암호화 키 생성 완료 (`secrets/encryption.key`)

### 의존성
- [ ] Python 가상환경 활성화
- [ ] `pip install -r requirements.txt` 완료
- [ ] `playwright install chromium` 완료
- [ ] Node.js 설치 확인 (`node --version`)
- [ ] MCP 서버 전역 설치 완료

### 데이터베이스
- [ ] `data/` 디렉토리 생성
- [ ] SQLite 또는 PostgreSQL 설정 완료
- [ ] 데이터베이스 스키마 초기화

### API 키
- [ ] Anthropic API 키 발급 및 저장
- [ ] Google API 키 발급 및 저장
- [ ] Perplexity API 키 발급 및 저장
- [ ] (선택) Brave API 키 발급

### 테스트
- [ ] Research Agent 테스트 통과
- [ ] Content Agent 테스트 통과
- [ ] Visual Agent 테스트 통과
- [ ] Playwright 로그인 테스트 통과

---

## 🛠 문제 해결

### 키체인 접근 오류
```bash
# macOS에서 키체인 접근 권한 오류 시
security unlock-keychain ~/Library/Keychains/login.keychain-db
```

### Playwright 브라우저 오류
```bash
# 브라우저 재설치
playwright install --force chromium
```

### PostgreSQL 연결 오류
```bash
# PostgreSQL 상태 확인
brew services list | grep postgresql

# 재시작
brew services restart postgresql@15
```

### MCP 서버 오류
```bash
# Node.js 버전 확인 (18.0 이상 필요)
node --version

# MCP 서버 재설치
npm uninstall -g @modelcontextprotocol/server-*
npm install -g @modelcontextprotocol/server-sequential-thinking
```

---

## 📚 다음 단계

1. **[FINAL_MASTER_PLAN.md](FINAL_MASTER_PLAN.md)** - 전체 로드맵 확인
2. **[SECURITY_ALERT.md](SECURITY_ALERT.md)** - 보안 수칙 숙지
3. 각 Phase별 구현 시작

---

## 💬 도움이 필요하신가요?

- 기술 문서: 각 MD 파일 참고
- 코드 예제: `examples/` 디렉토리 (추후 추가 예정)
- 이슈 리포팅: GitHub Issues 또는 텔레그램 알림 확인

**Happy Coding! 🎉**
