"""
취소선 버튼 정확한 상태 디버깅
- 제공된 정확한 셀렉터로 버튼 찾기
- 활성화 상태 감지 방법 파악
"""

import asyncio
from patchright.async_api import async_playwright
from loguru import logger
from pathlib import Path
import json


async def debug_strikethrough():
    """취소선 버튼 상태 디버깅"""

    async with async_playwright() as p:
        # 세션 로드
        from security.session_manager import SecureSessionManager
        session_manager = SecureSessionManager()
        state = session_manager.load_session("wncksdid0750_clipboard")

        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state=state)
        page = await context.new_page()

        # 글쓰기 페이지로 이동
        await page.goto("https://blog.naver.com/wncksdid0750/postwrite")
        await asyncio.sleep(3)

        # 팝업 처리
        try:
            cancel_btn = page.locator('button:has-text("취소")').first
            if await cancel_btn.is_visible(timeout=2000):
                await cancel_btn.click()
                await asyncio.sleep(1)
        except:
            pass

        try:
            close_btn = page.locator('button.se-help-panel-close-button').first
            if await close_btn.is_visible(timeout=1000):
                await close_btn.click()
                await asyncio.sleep(0.5)
        except:
            pass

        # 본문 클릭
        content_area = page.locator('.se-section-text p').first
        await content_area.click()
        await asyncio.sleep(1)

        print("\n" + "=" * 70)
        print("1단계: 취소선 버튼 찾기 (정확한 셀렉터)")
        print("=" * 70)

        # 정확한 셀렉터로 버튼 찾기
        btn_info = await page.evaluate('''
            () => {
                const selectors = [
                    'button.se-strikethrough-toolbar-button',
                    'button[data-name="strikethrough"]',
                    '.se-strikethrough-toolbar-button'
                ];

                for (const sel of selectors) {
                    const btn = document.querySelector(sel);
                    if (btn) {
                        return {
                            found: true,
                            selector: sel,
                            className: btn.className,
                            outerHTML: btn.outerHTML.substring(0, 500),
                            parentClassName: btn.parentElement?.className || '',
                            parentOuterHTML: btn.parentElement?.outerHTML.substring(0, 300) || ''
                        };
                    }
                }
                return { found: false };
            }
        ''')

        print(f"버튼 발견: {btn_info.get('found')}")
        if btn_info.get('found'):
            print(f"셀렉터: {btn_info.get('selector')}")
            print(f"클래스: {btn_info.get('className')}")
            print(f"부모 클래스: {btn_info.get('parentClassName')}")
            print(f"\n버튼 HTML:\n{btn_info.get('outerHTML')}")
            print(f"\n부모 HTML:\n{btn_info.get('parentOuterHTML')}")

        print("\n" + "=" * 70)
        print("2단계: 텍스트 입력 후 취소선 버튼 상태 확인")
        print("=" * 70)

        # 텍스트 입력
        await page.keyboard.type("테스트 텍스트입니다.", delay=50)
        await asyncio.sleep(1)

        # 전체 선택
        await page.keyboard.press("Meta+KeyA")
        await asyncio.sleep(0.5)

        # 버튼 상태 확인
        btn_state_before = await page.evaluate('''
            () => {
                const btn = document.querySelector('button.se-strikethrough-toolbar-button') ||
                           document.querySelector('button[data-name="strikethrough"]');
                if (!btn) return { error: '버튼 없음' };

                const parent = btn.parentElement;
                const wrapper = btn.closest('[class*="toolbar-button"]');

                return {
                    // 버튼 자체 속성
                    btnClassName: btn.className,
                    btnAriaPressed: btn.getAttribute('aria-pressed'),
                    btnDataState: btn.getAttribute('data-state'),

                    // 부모 요소
                    parentClassName: parent?.className || '',
                    parentTagName: parent?.tagName || '',

                    // wrapper 요소
                    wrapperClassName: wrapper?.className || '',

                    // 활성화 체크
                    hasActiveInBtn: btn.className.includes('active'),
                    hasActiveInParent: (parent?.className || '').includes('active'),
                    hasActiveInWrapper: (wrapper?.className || '').includes('active'),

                    // SVG 색상 확인
                    svgFill: (() => {
                        const svg = btn.querySelector('svg');
                        if (!svg) return 'svg 없음';
                        const paths = svg.querySelectorAll('path');
                        const fills = [];
                        paths.forEach(p => fills.push(p.getAttribute('fill')));
                        return fills.join(', ');
                    })()
                };
            }
        ''')

        print("텍스트 선택 후 (취소선 클릭 전):")
        print(json.dumps(btn_state_before, indent=2, ensure_ascii=False))

        print("\n" + "=" * 70)
        print("3단계: 취소선 버튼 클릭 후 상태 변화 확인")
        print("=" * 70)

        # 취소선 버튼 클릭
        await page.evaluate('''
            () => {
                const btn = document.querySelector('button.se-strikethrough-toolbar-button') ||
                           document.querySelector('button[data-name="strikethrough"]');
                if (btn) btn.click();
            }
        ''')
        await asyncio.sleep(0.5)

        # 버튼 상태 다시 확인
        btn_state_after = await page.evaluate('''
            () => {
                const btn = document.querySelector('button.se-strikethrough-toolbar-button') ||
                           document.querySelector('button[data-name="strikethrough"]');
                if (!btn) return { error: '버튼 없음' };

                const parent = btn.parentElement;
                const wrapper = btn.closest('[class*="toolbar-button"]');

                return {
                    btnClassName: btn.className,
                    btnAriaPressed: btn.getAttribute('aria-pressed'),
                    parentClassName: parent?.className || '',
                    wrapperClassName: wrapper?.className || '',
                    hasActiveInBtn: btn.className.includes('active'),
                    hasActiveInParent: (parent?.className || '').includes('active'),
                    hasActiveInWrapper: (wrapper?.className || '').includes('active'),
                    svgFill: (() => {
                        const svg = btn.querySelector('svg');
                        if (!svg) return 'svg 없음';
                        const paths = svg.querySelectorAll('path');
                        const fills = [];
                        paths.forEach(p => fills.push(p.getAttribute('fill')));
                        return fills.join(', ');
                    })()
                };
            }
        ''')

        print("취소선 버튼 클릭 후:")
        print(json.dumps(btn_state_after, indent=2, ensure_ascii=False))

        # 변화 분석
        print("\n" + "=" * 70)
        print("4단계: 상태 변화 분석")
        print("=" * 70)

        print("\n[변화된 항목]")
        for key in btn_state_before:
            if key in btn_state_after:
                before = btn_state_before[key]
                after = btn_state_after[key]
                if before != after:
                    print(f"  {key}: '{before}' → '{after}'")

        print("\n" + "=" * 70)
        print("5단계: 인라인 툴바 확인 (텍스트 선택 시 나타나는 툴바)")
        print("=" * 70)

        # 인라인 툴바 확인
        inline_toolbar = await page.evaluate('''
            () => {
                // 인라인 툴바 (텍스트 선택 시 나타나는 플로팅 툴바)
                const inlineToolbar = document.querySelector('.se-inline-toolbar') ||
                                     document.querySelector('[class*="inline-toolbar"]') ||
                                     document.querySelector('[class*="property-toolbar"]');

                if (!inlineToolbar) return { found: false };

                const buttons = inlineToolbar.querySelectorAll('button');
                const btnInfos = [];

                buttons.forEach((btn, i) => {
                    btnInfos.push({
                        index: i,
                        dataName: btn.getAttribute('data-name'),
                        className: btn.className,
                        isVisible: btn.offsetParent !== null
                    });
                });

                return {
                    found: true,
                    className: inlineToolbar.className,
                    isVisible: inlineToolbar.offsetParent !== null,
                    style: inlineToolbar.getAttribute('style'),
                    buttons: btnInfos
                };
            }
        ''')

        print(json.dumps(inline_toolbar, indent=2, ensure_ascii=False))

        print("\n디버깅을 위해 브라우저를 30초간 유지합니다...")
        print("개발자 도구(F12)에서 직접 확인해보세요.")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_strikethrough())
