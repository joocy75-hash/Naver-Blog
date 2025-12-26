# 🚨 긴급 보안 알림

## 발견된 치명적 보안 취약점

`.env.example` 파일에 **실제 API 키와 비밀번호**가 노출되어 있었습니다.

### 노출된 정보

1. **네이버 계정**: ID와 비밀번호
2. **Anthropic API Key**: Claude 사용 키
3. **Google API Key**: Gemini 사용 키
4. **Perplexity API Key**: 검색 API 키

---

## ⚠️ 즉시 취해야 할 조치

### 1. API 키 즉시 재발급 (필수)

#### Anthropic (Claude)
1. https://console.anthropic.com/ 접속
2. Settings → API Keys
3. 기존 키 삭제 (Revoke)
4. 새 키 발급

#### Google (Gemini)
1. https://ai.google.dev/ 접속
2. API Keys 메뉴
3. 기존 키 삭제
4. 새 키 발급

#### Perplexity
1. https://www.perplexity.ai/settings/api 접속
2. 기존 키 삭제
3. 새 키 발급

### 2. 네이버 비밀번호 변경
1. 네이버 로그인 → 내정보 → 보안설정
2. 비밀번호 즉시 변경
3. 2단계 인증 활성화 권장

### 3. Git 히스토리 정리 (중요!)

만약 이 파일을 Git에 커밋했다면:

```bash
# Git 히스토리에서 민감 정보 완전 제거
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env.example" \
  --prune-empty --tag-name-filter cat -- --all

# 강제 푸시 (원격 저장소가 있는 경우)
git push origin --force --all
```

**경고**: 이미 GitHub/GitLab 등에 푸시했다면 저장소를 private으로 전환하거나 삭제하고 새로 만드는 것을 권장합니다.

---

## 🛡️ 앞으로의 보안 수칙

### 1. 환경 변수 분리
```bash
# .env.example: 템플릿만 (실제 값 절대 금지)
NAVER_ID=your_naver_id

# .env: 실제 값 (Git에 커밋 절대 금지)
NAVER_ID=wncksdid0750
```

### 2. .gitignore 확인
```bash
# 항상 확인할 것
cat .gitignore | grep ".env"
```

### 3. 키체인 사용 (권장)

Python 코드에서:
```python
import keyring

# 저장
keyring.set_password("naver_blog", "wncksdid0750", "새비밀번호")

# 불러오기
password = keyring.get_password("naver_blog", "wncksdid0750")
```

### 4. 커밋 전 체크리스트
- [ ] `.env` 파일이 .gitignore에 있는가?
- [ ] `git status`로 민감 파일이 추가되지 않았는가?
- [ ] `.env.example`에 실제 값이 없는가?

---

## 📋 체크리스트

- [ ] Anthropic API 키 재발급 완료
- [ ] Google API 키 재발급 완료
- [ ] Perplexity API 키 재발급 완료
- [ ] 네이버 비밀번호 변경 완료
- [ ] 네이버 2단계 인증 활성화
- [ ] Git 히스토리 정리 (해당 시)
- [ ] 새 API 키를 `.env` 파일에만 저장
- [ ] `.env.example` 파일 확인 (템플릿만 있어야 함)
- [ ] `.gitignore` 확인

---

## 💡 보안 모범 사례

1. **절대 공유 금지**: API 키, 비밀번호는 어디에도 공유하지 않기
2. **정기 교체**: 3개월마다 API 키 교체
3. **권한 최소화**: 각 API 키에 필요한 최소 권한만 부여
4. **모니터링**: API 사용량 주기적 확인 (비정상 사용 감지)
5. **2FA 활성화**: 모든 계정에 2단계 인증 설정

---

**작성일**: 2025-12-22
**긴급도**: 🔴 Critical
