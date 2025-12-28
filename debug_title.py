"""제목 입력 디버그 스크립트 (개선 버전)

이 스크립트로 제목 입력 문제를 진단합니다:
1. 팝업 처리
2. 부모 요소 체인 분석
3. bounding_box 클릭 테스트
4. dispatchEvent 테스트
"""

import asyncio
from playwright.async_api import async_playwright
from security.session_manager import SecureSessionManager


async def debug():
    sm = SecureSessionManager()
    state = sm.load_session("wncksdid0750_clipboard")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=state, viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        # 글쓰기 페이지
        print("=" * 60)
        print("1. 글쓰기 페이지 이동")
        print("=" * 60)
        await page.goto("https://blog.naver.com/wncksdid0750/postwrite")
        await asyncio.sleep(5)

        print("\n2. 팝업 처리")
        # 팝업 취소
        popup_result = await page.evaluate("""
            () => {
                const cancelBtn = document.querySelector('.se-popup-button-cancel') ||
                    Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('취소'));
                if (cancelBtn) { 
                    cancelBtn.click(); 
                    return 'clicked: ' + cancelBtn.textContent; 
                }
                return 'no popup found';
            }
        """)
        print(f"   팝업 결과: {popup_result}")
        await asyncio.sleep(2)

        # 도움말 닫기 + 오버레이 제거
        removed = await page.evaluate("""
            () => {
                let removed = 0;
                
                // 도움말 컨테이너 숨김
                const helpContainers = document.querySelectorAll('[class*="container__HW"], .se-help-panel');
                helpContainers.forEach(el => { el.style.display = 'none'; removed++; });
                
                // 팝업/오버레이 완전 제거
                const overlays = document.querySelectorAll('.se-popup-dim, .se-popup-dim-white, .se-popup');
                overlays.forEach(el => { 
                    el.style.display = 'none';
                    el.remove();
                    removed++;
                });
                
                return removed;
            }
        """)
        print(f"   제거된 요소: {removed}개")
        await asyncio.sleep(3)  # 에디터 재활성화 대기

        print("\n3. 제목 요소 분석")
        title_info = await page.evaluate("""
            () => {
                const selectors = [
                    '.se-section-documentTitle p',
                    '.se-section-documentTitle .se-text-paragraph',
                    '.se-documentTitle p',
                    '.se-section-documentTitle'
                ];

                const results = [];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const rect = el.getBoundingClientRect();
                        results.push({
                            selector: sel,
                            exists: true,
                            offsetParent: el.offsetParent ? el.offsetParent.tagName : 'null',
                            display: getComputedStyle(el).display,
                            visibility: getComputedStyle(el).visibility,
                            pointerEvents: getComputedStyle(el).pointerEvents,
                            width: rect.width,
                            height: rect.height,
                            x: rect.x,
                            y: rect.y
                        });
                    } else {
                        results.push({ selector: sel, exists: false });
                    }
                }
                return results;
            }
        """)

        for info in title_info:
            print(f"\n   [{info['selector']}]")
            if info.get("exists"):
                print(f"      offsetParent: {info.get('offsetParent')}")
                print(
                    f"      display: {info.get('display')}, visibility: {info.get('visibility')}"
                )
                print(f"      pointerEvents: {info.get('pointerEvents')}")
                print(
                    f"      rect: x={info.get('x'):.0f}, y={info.get('y'):.0f}, w={info.get('width'):.0f}, h={info.get('height'):.0f}"
                )
            else:
                print("      요소 없음")

        print("\n4. 부모 요소 체인 분석")
        parent_chain = await page.evaluate("""
            () => {
                const el = document.querySelector('.se-section-documentTitle p');
                if (!el) return { error: 'not found' };
                
                const parents = [];
                let current = el;
                while (current && current !== document.body) {
                    const style = getComputedStyle(current);
                    parents.push({
                        tag: current.tagName,
                        class: current.className.slice(0, 50),
                        display: style.display,
                        visibility: style.visibility,
                        pointerEvents: style.pointerEvents
                    });
                    current = current.parentElement;
                }
                return parents;
            }
        """)

        if isinstance(parent_chain, list):
            for i, p in enumerate(parent_chain[:10]):
                hidden = (
                    "❌"
                    if p["display"] == "none" or p["visibility"] == "hidden"
                    else "✅"
                )
                print(
                    f"   {hidden} [{i}] {p['tag']}: display={p['display']}, visibility={p['visibility']}, pointerEvents={p['pointerEvents']}"
                )
        else:
            print(f"   오류: {parent_chain}")

        print("\n5. bounding_box 클릭 테스트")
        title_section = await page.query_selector(".se-section-documentTitle")
        if title_section:
            box = await title_section.bounding_box()
            if box and box["width"] > 0:
                click_x = box["x"] + box["width"] / 2
                click_y = box["y"] + box["height"] / 2
                print(f"   클릭 좌표: ({click_x:.0f}, {click_y:.0f})")
                await page.mouse.click(click_x, click_y)
                await asyncio.sleep(0.5)

                # 포커스 확인
                focused = await page.evaluate("""
                    () => {
                        const active = document.activeElement;
                        return {
                            tagName: active.tagName,
                            className: active.className.slice(0, 50),
                            contentEditable: active.contentEditable
                        };
                    }
                """)
                print(f"   활성 요소: {focused}")
            else:
                print("   bounding_box 없음")
        else:
            print("   제목 섹션 없음")

        print("\n6. 키보드 입력 테스트")
        await page.keyboard.type("테스트 제목 12345", delay=50)
        await asyncio.sleep(1)

        # 입력된 내용 확인
        typed = await page.evaluate("""
            () => {
                const titleEl = document.querySelector('.se-section-documentTitle p');
                return titleEl ? titleEl.innerText : 'not found';
            }
        """)
        print(f"   입력된 제목: '{typed}'")

        if "테스트 제목" in typed:
            print("   ✅ 제목 입력 성공!")
        else:
            print("   ❌ 제목 입력 실패")

        # 스크린샷
        screenshot_path = "./logs/debug_title.png"
        await page.screenshot(path=screenshot_path)
        print(f"\n7. 스크린샷 저장: {screenshot_path}")

        await browser.close()
        print("\n" + "=" * 60)
        print("디버그 완료")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(debug())
