# Naver Blog Automation - Technical Specifications

본 문서는 Playwright를 이용한 네이버 블로그 자동 업로드의 기술적 난제와 해결 방안을 상세히 다룹니다.

## 1. 스마트에디터 ONE 인터랙션 전략

네이버 블로그의 '스마트에디터 ONE'은 일반적인 HTML Form이 아니며, 복잡한 React/Vue 기반의 에디터입니다.

### 1.1. 제목 입력

- Selector: `textarea.textarea_input` (클래스명은 변경될 수 있음)
- 전략: `page.fill()` 대신 `page.click()` 후 `page.keyboard.type()`을 사용하여 실제 타이핑 시뮬레이션.

### 1.2. 본문 입력 (가장 까다로운 부분)

- **문제**: 본문 영역은 `contenteditable` 속성을 가진 여러 개의 `div` 또는 `p` 태그로 구성됩니다. 단순히 `fill`을 사용하면 에디터 내부 상태와 동기화되지 않아 글이 사라질 수 있습니다.
- **해결책 (Clipboard 방식)**:
  1. 생성된 HTML/Markdown 본문을 브라우저의 클립보드에 복사합니다.
  2. 에디터 본문 영역을 클릭합니다.
  3. `page.keyboard.press('Control+V')` (또는 `Meta+V`)를 실행합니다.
  4. 이 방식은 네이버 에디터가 외부 콘텐츠를 붙여넣을 때 수행하는 내부 파싱 로직을 그대로 타게 하므로 가장 안정적입니다.

### 1.3. 이미지 업로드

- **방법 A (Input File)**: 숨겨진 `input[type="file"]` 요소를 찾아 `set_input_files()`를 호출합니다.
- **방법 B (Drag & Drop)**: Playwright의 `drag_and_drop` 기능을 사용하여 로컬 파일을 에디터 영역으로 끌어다 놓습니다. (방법 A가 더 안정적임)

## 2. 봇 탐지 우회 (Anti-Bot)

### 2.1. Human-like Behavior

- **Mouse Movement**: 클릭 전 마우스를 해당 요소 근처로 랜덤하게 이동시키는 `page.mouse.move()` 사용.
- **Typing Speed**: `keyboard.type(text, delay=random.uniform(50, 150))`을 통해 타이핑 속도 조절.
- **Scroll**: 페이지 하단까지 천천히 스크롤하여 실제 읽는 듯한 동작 추가.

### 2.2. Fingerprinting 방지

- `playwright-stealth` 라이브러리(Python 포팅 버전)를 사용하여 `navigator.webdriver` 등 봇 감지 속성 제거.
- `User-Agent`를 최신 Chrome 버전으로 상시 업데이트.

## 3. 세션 유지 및 관리

### 3.1. Storage State

- 로그인 성공 후 `context.storage_state(path="auth/state.json")`를 호출하여 쿠키 및 로컬 스토리지를 저장합니다.
- 이후 실행 시 `browser.new_context(storage_state="auth/state.json")`으로 세션을 복구합니다.

### 3.2. 2차 인증 (2FA) 대응

- 세션이 만료되어 재로그인이 필요한 경우, 텔레그램 봇으로 알림을 보내고 사용자가 수동으로 로그인할 수 있는 '수동 모드' 브라우저를 띄우는 로직이 필요합니다.

## 4. 에러 핸들링 및 복구

- **Timeout**: 네이버 서버 응답 지연 시 `try-except`로 재시도 로직 구현.
- **Element Not Found**: 에디터 구조 변경 시 즉시 알림을 보내고 작업을 중단하여 계정 보호.
