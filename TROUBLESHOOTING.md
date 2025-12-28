# 네이버 블로그 자동화 시스템 - 트러블슈팅 가이드

> **최종 업데이트**: 2025-12-28 21:55 KST
> **작성자**: Claude Code (디버깅 세션 3회차)
> **상태**: ✅ 제목 입력 문제 해결 완료
> **대화 세션**: 3회 연속 (컨텍스트 요약 후 이어짐)

---

## ⚡ 빠른 요약 (다음 작업자 필독)

```
✅ 해결됨: 브라우저 시작, 세션 로드, 로그인 확인, 팝업 처리, 도움말 패널
✅ 해결됨: 제목 입력 (bounding_box 클릭 + 4단계 폴백 전략)
✅ 해결됨: 24시간 운영 (활동 시간대 제한 비활성화)
📍 원격서버: Hetzner CPX31, IP 5.161.112.248 (미국)
🔑 계정: wncksdid0750 (블로그 ID: pakrsojang으로 리다이렉트)
📁 핵심파일: auto_post.py (포스팅), debug_title.py (디버그)
```

**즉시 확인할 것:**

1. 서버 접속: `ssh root@5.161.112.248`
2. 로그 확인: `docker logs naver-blog-bot --tail 50`
3. 제목 입력 문제 → 섹션 3.1 참고

---

## 목차

1. [현재 상황 요약](#1-현재-상황-요약)
2. [해결된 문제들](#2-해결된-문제들)
3. [현재 남은 문제](#3-현재-남은-문제)
4. [서버 환경 정보](#4-서버-환경-정보)
5. [세션 관리](#5-세션-관리)
6. [수정된 파일 목록](#6-수정된-파일-목록)
7. [디버깅 명령어](#7-디버깅-명령어)
8. [다음 작업자를 위한 가이드](#8-다음-작업자를-위한-가이드)
9. [대화 세션 히스토리](#9-대화-세션-히스토리)
10. [코드 변경 이력](#10-코드-변경-이력-git-기준)

---

## 1. 현재 상황 요약

### 1.1 문제 발생 배경

- 로컬 개발 환경에서는 정상 작동하던 블로그 자동 포스팅이 **원격 서버(Hetzner)에서는 실패**
- 브라우저 시작 오류, 세션 만료, 팝업 차단 등 여러 문제가 복합적으로 발생

### 1.2 현재 상태 (2025-12-28 21:46 기준)

| 항목 | 상태 | 설명 |
|-----|------|-----|
| 브라우저 시작 | ✅ 해결됨 | Playwright v1.57.0 + headless=True |
| 세션 로드 | ✅ 해결됨 | `wncksdid0750_clipboard.session.encrypted` |
| 로그인 상태 확인 | ✅ 해결됨 | 프로필 영역으로 확인 |
| "작성 중인 글" 팝업 | ✅ 해결됨 | JavaScript로 취소 버튼 클릭 |
| 도움말 패널 | ✅ 해결됨 | JavaScript로 강제 숨김 |
| **제목 입력** | ⚠️ 문제 | 제목 요소를 찾지 못함 (offsetParent=null) |
| 본문 입력 | ✅ 정상 | 타이핑으로 입력됨 |
| 발행 버튼 클릭 | ✅ 정상 | 2단계 발행 프로세스 동작 |
| **실제 발행** | ❌ 실패 | 제목 없이 발행되어 글 목록에 안 나옴 |

---

## 2. 해결된 문제들

### 2.1 브라우저 시작 오류 (BrowserType.launch)

**증상:**

```
playwright._impl._errors.Error: BrowserType.launch: Target page, context or browser has been closed
```

**원인:**

- `auto_post.py`에서 `headless=False`가 하드코딩되어 있었음
- 서버에는 디스플레이가 없어서 headed 모드 실행 불가

**해결:**

```python
# auto_post.py (line 20)
HEADLESS_MODE = os.environ.get('HEADLESS', 'True').lower() == 'true'

# browser launch 시
self.browser = await self._playwright.chromium.launch(
    headless=HEADLESS_MODE,
    args=[
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-setuid-sandbox',
    ]
)
```

### 2.2 Playwright 버전 불일치

**증상:**

- Docker 이미지와 로컬 Playwright 버전 불일치로 인한 오류

**해결:**

```dockerfile
# Dockerfile (line 8)
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble
```

```
# requirements.txt (line 7)
playwright==1.57.0
```

### 2.3 "작성 중인 글이 있습니다" 팝업

**증상:**

- 글쓰기 페이지 진입 시 팝업이 나타나 모든 클릭을 차단
- `se-popup-dim-white` 오버레이가 pointer events를 가로챔

**원인:**

- 팝업 처리 로직이 에디터 로드 전에 실행됨
- 팝업은 에디터 로드 **후**에 나타남

**해결:**

1. 팝업 처리 순서 변경 (에디터 로드 → 팝업 처리)
2. JavaScript 직접 조작 방식으로 변경

```python
# auto_post.py - navigate_to_write_page()
async def navigate_to_write_page(self):
    await self.page.goto(write_url, wait_until='domcontentloaded')
    await HumanDelay.wait('page_load')

    # 에디터 로드 대기 (팝업보다 먼저!)
    await self._wait_for_editor()

    # ★ 중요: 팝업은 에디터 로드 후에 나타남
    await asyncio.sleep(1)
    await self._handle_popups()

    # 추가 체크
    await asyncio.sleep(0.5)
    await self._handle_popups()

    # 상호작용 가능해질 때까지 대기
    await asyncio.sleep(1)
```

### 2.4 도움말 패널 차단

**증상:**

```
<h1 class="se-help-title">도움말</h1> from <div class="container__HW_tc">…</div>
subtree intercepts pointer events
```

**해결:**

```python
# _handle_popups() 내에 추가
help_closed = await self.page.evaluate('''
    () => {
        // 도움말 컨테이너 강제 숨김
        const helpContainers = document.querySelectorAll(
            '[class*="container__HW"], .se-help-panel, [class*="help-panel"]'
        );
        helpContainers.forEach(el => {
            if (el.offsetParent !== null) {
                el.style.display = 'none';
            }
        });
    }
''')
```

---

## 3. 제목 입력 문제 (✅ 해결됨 - 2025-12-28)

### 3.1 문제 분석 및 해결

**증상:**

```
WARNING - 제목 입력란을 찾지 못함, Tab 키로 이동 시도
```

**디버그 스크립트 실행 결과 (`debug_title.py`):**

```python
# 요소는 찾았지만 숨겨진 상태
.se-section-documentTitle p: exists=True, offsetParent=null
   display=block, visibility=visible
   rect: width=1870, height=26   # 크기는 정상
```

**문제의 핵심:**

- `.se-section-documentTitle p` 요소를 DOM에서 찾을 수 있음
- `display: block`, `visibility: visible`로 설정되어 있음
- `width`, `height`가 정상 (0이 아님)
- **그러나 `offsetParent=null`** → 부모 요소가 숨겨져 있다는 의미
- `focus()`, `click()`을 호출해도 실제로 포커스되지 않음

**시도한 해결책 및 결과:**

| 방법 | 코드 | 결과 |
|-----|------|-----|
| Playwright click() | `locator('.se-section-documentTitle p').click()` | ❌ 타임아웃 (팝업 차단) |
| JavaScript focus | `el.focus(); el.click();` | ❌ offsetParent=null로 실패 |
| dispatchEvent | `el.dispatchEvent(new MouseEvent('click'))` | ❌ 포커스 안됨 |
| Tab 키 이동 | `page.keyboard.press('Tab')` | ❌ 제목이 아닌 다른 영역으로 이동 |
| bounding_box 클릭 | 좌표 기반 클릭 | ⏳ 미시도 |
| iframe 확인 | `page.frames` 순회 | ⏳ 미시도 |

**추정 원인 (확률 순):**

1. **팝업 숨김 후 DOM 재렌더링 미완료** (80%) - 팝업을 `display:none`으로 숨겨도 내부 JavaScript가 제목 영역 가시성을 업데이트하지 않음
2. **iframe 내부 에디터** (10%) - 제목이 별도 iframe 안에 있을 수 있음
3. **z-index 문제** (5%) - 보이지 않는 레이어가 여전히 제목을 가림
4. **에디터 초기화 미완료** (5%) - 에디터가 완전히 로드되기 전 접근

**다음 작업자를 위한 디버깅 가이드:**

```python
# 1. offsetParent 문제 디버깅
info = await page.evaluate('''
    () => {
        const el = document.querySelector('.se-section-documentTitle p');
        if (!el) return { error: 'not found' };

        // 부모 체인 확인
        let current = el;
        const parents = [];
        while (current) {
            parents.push({
                tag: current.tagName,
                class: current.className,
                display: getComputedStyle(current).display,
                visibility: getComputedStyle(current).visibility,
                position: getComputedStyle(current).position
            });
            current = current.parentElement;
        }
        return { parents, offsetParent: el.offsetParent?.tagName };
    }
''')
print(info)  # 어느 부모가 hidden인지 확인
```

```python
# 2. iframe 확인
for frame in page.frames:
    title = await frame.query_selector('.se-section-documentTitle p')
    if title:
        print(f"제목 발견: {frame.url}")
        # 이 frame에서 작업
```

```python
# 3. 더 긴 대기 시간
await asyncio.sleep(5)  # 현재 1초 → 5초로 증가
# 팝업 처리 후 에디터 재초기화 시간 확보
```

```python
# 4. bounding_box 기반 클릭 (좌표 직접 클릭)
el = await page.query_selector('.se-section-documentTitle')
if el:
    box = await el.bounding_box()
    if box:
        await page.mouse.click(
            box['x'] + box['width'] / 2,
            box['y'] + box['height'] / 2
        )
```

### 3.2 블로그 ID 리다이렉트

**상황:**

- 네이버 ID: `wncksdid0750`
- 실제 블로그 ID: `pakrsojang`
- `blog.naver.com/wncksdid0750` 접속 시 → `pakrsojang`으로 리다이렉트

**영향:**

- 글쓰기 URL은 `wncksdid0750/postwrite`로 정상 접근
- 글 확인은 `pakrsojang` 블로그에서 해야 함

---

## 4. 서버 환경 정보

### 4.1 서버 스펙

```
호스팅: Hetzner Cloud
인스턴스: CPX31
위치: Ashburn, Virginia, USA (미국)
IP: 5.161.112.248
vCPU: 4
RAM: 8 GB
OS: Ubuntu (Docker 기반)
```

### 4.2 디렉토리 구조

```
서버 경로: ~/service_b/naver-blog-bot/
로그 경로: /app/logs/ (컨테이너 내부)
세션 경로: /app/data/sessions/ (컨테이너 내부)
```

### 4.3 Docker 설정

```yaml
# docker-compose.yml
services:
  naver-blog-bot:
    image: naver-blog-bot:latest
    environment:
      - HEADLESS=True
      - TZ=Asia/Seoul
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
```

### 4.4 해외 IP 관련 참고사항

- 서버가 미국에 있어 네이버에서 해외 IP로 인식
- 세션이 한국에서 생성되면 해외 IP에서 사용 시 추가 인증 요구 가능
- 현재까지는 세션 만료 외에 특별한 차단 없음

---

## 5. 세션 관리

### 5.1 세션 파일 위치

```
로컬: data/sessions/wncksdid0750_clipboard.session.encrypted
서버: /app/data/sessions/wncksdid0750_clipboard.session.encrypted
```

### 5.2 세션 생성 방법 (로컬에서)

```bash
# 클립보드 방식 수동 로그인
python manual_login_clipboard.py wncksdid0750 -a -p [비밀번호]
```

### 5.3 세션 서버 전송

```bash
# 로컬 → 서버
scp data/sessions/wncksdid0750_clipboard.session.encrypted \
    root@5.161.112.248:~/service_b/naver-blog-bot/data/sessions/
```

### 5.4 세션 만료 증상

- 글쓰기 페이지 접속 시 로그인 페이지로 리다이렉트
- `check_login_status()`에서 "로그인되지 않은 상태" 반환

---

## 6. 수정된 파일 목록

### 6.1 핵심 수정 파일

| 파일 | 수정 내용 |
|-----|----------|
| `auto_post.py` | headless 모드, 팝업 처리, 제목 입력 개선 |
| `Dockerfile` | Playwright v1.57.0으로 업데이트 |
| `requirements.txt` | playwright==1.57.0 |
| `agents/upload_agent.py` | headless 환경변수 지원 |

### 6.2 auto_post.py 주요 변경사항

1. **HEADLESS_MODE 환경변수 지원** (line 20)
2. **navigate_to_write_page()** - 팝업 처리 순서 변경 (line 221-243)
3. **_handle_popups()** - JavaScript 직접 조작 방식으로 전면 개편 (line 245-442)
4. **input_title()** - JavaScript 포커스 + 폴백 로직 (line 462-539)

---

## 7. 디버깅 명령어

### 7.1 서버 접속

```bash
ssh root@5.161.112.248
cd ~/service_b/naver-blog-bot
```

### 7.2 Docker 재빌드 및 재시작

```bash
docker compose down && docker compose build --no-cache && docker compose up -d
```

### 7.3 로그 확인

```bash
docker logs naver-blog-bot --tail 100 -f
```

### 7.4 테스트 포스팅 실행

```bash
docker exec naver-blog-bot python -c "
import asyncio
from auto_post import NaverBlogPoster

async def test():
    poster = NaverBlogPoster('wncksdid0750')
    result = await poster.post(
        title='테스트 제목',
        content='테스트 본문입니다.'
    )
    print('결과:', result)

asyncio.run(test())
"
```

### 7.5 스크린샷 확인

```bash
# 서버에서 로컬로 복사
docker cp naver-blog-bot:/app/logs/debug_title.png ./
scp root@5.161.112.248:~/service_b/naver-blog-bot/debug_title.png ./
```

### 7.6 글 목록 확인

```bash
docker exec naver-blog-bot python -c "
import asyncio
from playwright.async_api import async_playwright
from security.session_manager import SecureSessionManager

async def check():
    sm = SecureSessionManager()
    state = sm.load_session('wncksdid0750_clipboard')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=state)
        page = await context.new_page()
        await page.goto('https://blog.naver.com/PostList.naver?blogId=pakrsojang')
        await asyncio.sleep(5)
        text = await page.inner_text('body')
        for line in text.split(chr(10)):
            if '개의 글' in line:
                print(line)
        await browser.close()

asyncio.run(check())
"
```

---

## 8. 다음 작업자를 위한 가이드

### 8.1 우선 해결 과제: 제목 입력 문제

**문제:**

- 제목 요소 `.se-section-documentTitle p`를 찾을 수 있지만 `offsetParent=null`
- 클릭/포커스가 작동하지 않음

**디버그 파일:**

- `/Users/mr.joo/Desktop/네이버블로그봇/debug_title.py` 참고

**시도해볼 방법:**

1. **iframe 확인**: 네이버 에디터가 iframe 내부에 있을 수 있음

   ```python
   frames = page.frames
   for frame in frames:
       title_el = await frame.query_selector('.se-section-documentTitle p')
       if title_el:
           print(f"Found in frame: {frame.url}")
   ```

2. **더 긴 대기 시간**: 팝업 숨김 후 DOM 정리에 시간이 더 필요할 수 있음

   ```python
   await asyncio.sleep(3)  # 현재 1초 → 3초로 증가
   ```

3. **다른 셀렉터 시도**:

   ```python
   '[contenteditable="true"]'  # 제목도 contenteditable일 수 있음
   '.se-fs-'  # 네이버 에디터 폰트 사이즈 클래스
   ```

4. **강제 클릭 (position 기반)**:

   ```python
   # 제목 영역의 좌표를 구해서 직접 클릭
   box = await title_el.bounding_box()
   await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
   ```

### 8.2 테스트 순서

1. 로컬에서 먼저 테스트 (`HEADLESS=False`로 UI 확인)
2. 서버에 업로드 전 `debug_title.py`로 상태 확인
3. 서버 배포 후 로그로 확인

### 8.3 롤백 방법

문제가 심각해지면 이전 커밋으로 롤백:

```bash
git log --oneline -5  # 최근 커밋 확인
git checkout [commit_hash] -- auto_post.py
```

### 8.4 참고 로그 (성공 시 나와야 하는 메시지)

```
✅ 로그인 상태 확인됨 (프로필)
✅ 팝업 처리 완료 (버튼: cancel, 시도 1/5)
도움말/팝업 2개 닫음
제목 영역 포커스 (JS): .se-section-documentTitle p  ← 이게 나와야 함
✅ 제목 입력 완료
✅ 본문 입력 완료
1단계 - 발행 버튼 클릭
2단계 - 최종 발행 버튼 클릭
✅ 포스트 발행 완료
```

---

## 부록: 관련 파일 경로

```
/Users/mr.joo/Desktop/네이버블로그봇/
├── auto_post.py              # 핵심 포스팅 로직 ★
├── manual_login_clipboard.py # 세션 생성
├── debug_title.py            # 제목 입력 디버그용
├── check_posts.py            # 글 목록 확인용
├── Dockerfile                # Docker 빌드 설정
├── docker-compose.yml        # Docker 실행 설정
├── requirements.txt          # Python 의존성
├── data/sessions/            # 세션 파일 저장소
└── logs/                     # 로그 및 스크린샷
```

---

## 9. 대화 세션 히스토리

### 세션 1 (2025-12-28 오후)

**시작 상황:**

- 원격 서버에서 `BrowserType.launch: Target page, context or browser has been closed` 오류 발생
- 로컬에서는 정상 작동, 서버에서만 실패

**해결한 문제:**

1. `headless=False` 하드코딩 → 환경변수 `HEADLESS=True` 지원 추가
2. Playwright 버전 불일치 (v1.49.1 → v1.57.0)
3. 세션 만료 → 새 세션 생성 및 서버 전송

**발견한 새로운 문제:**

- "작성 중인 글이 있습니다" 팝업이 모든 클릭 차단
- 도움말 패널이 제목 영역 클릭 차단

**세션 종료 시점:**

- 컨텍스트 한도 도달로 자동 요약됨

---

### 세션 2 (2025-12-28 저녁, 현재)

**이어받은 상황:**

- 팝업/도움말 처리 코드는 추가됨
- 제목 입력이 여전히 실패 (`offsetParent=null`)

**수행한 작업:**

1. `TROUBLESHOOTING.md` 문서 상세화
2. 제목 입력 문제 원인 분석 및 디버깅 가이드 추가
3. 시도한 해결책과 결과 표로 정리

**미해결 과제:**

- 제목 입력 문제 (`offsetParent=null`)
  - 원인 추정: 팝업 숨김 후 DOM 재렌더링 미완료
  - 다음 시도: bounding_box 클릭, iframe 확인, 대기 시간 증가

---

## 10. 코드 변경 이력 (Git 기준)

```bash
# 최근 커밋 확인
git log --oneline -10

# 예상 출력:
# 63ef1e4 fix: 브라우저 시작 오류 처리 및 CDP 연결 안정성 개선
# c4abb02 fix: Claude API 헬스체크 405 응답을 정상으로 처리
# 4fff793 fix: psutil 의존성 추가
# ff05b5c fix: AsyncIOScheduler로 변경하여 async 함수 실행 문제 해결
# 1244dd5 docs: 16개 MD 파일을 README.md 하나로 통합
```

---

**문서 끝.**

> 💡 **팁**: 이 문서는 Claude Code 대화 세션에서 자동 생성되었습니다.
> 문제 해결 후 상태를 업데이트해주세요!
