"""
동적 인라인 툴바 분석 스크립트
- 텍스트 선택 시 나타나는 서식 버튼들 분석
- 취소선 버튼 정확한 셀렉터 찾기
"""

import asyncio
from playwright.async_api import async_playwright
from security.session_manager import SecureSessionManager
from loguru import logger


async def analyze_inline_toolbar():
    """텍스트 선택 시 나타나는 동적 툴바 분석"""
    
    naver_id = "wncksdid0750"
    sm = SecureSessionManager()
    session_data = sm.load_session(naver_id)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=session_data,
            viewport={"width": 1400, "height": 900}
        )
        page = await context.new_page()
        
        # 글쓰기 페이지 이동
        await page.goto(f"https://blog.naver.com/{naver_id}/postwrite")
        await asyncio.sleep(3)
        
        # 팝업 닫기
        try:
            popup_close = page.locator('.popup_btn_close')
            if await popup_close.is_visible(timeout=2000):
                await popup_close.click()
                await asyncio.sleep(0.5)
        except:
            pass
        
        logger.info("=" * 70)
        logger.info("1단계: 본문에 테스트 텍스트 입력")
        logger.info("=" * 70)
        
        # 본문 영역 찾기 및 클릭
        editor = page.locator('.se-component-content[contenteditable="true"]').first
        if not await editor.is_visible(timeout=3000):
            editor = page.locator('[contenteditable="true"]').first
        
        await editor.click()
        await asyncio.sleep(0.5)
        
        # 테스트 텍스트 입력
        await page.keyboard.type("테스트 텍스트입니다. 이 텍스트를 선택하겠습니다.", delay=50)
        await asyncio.sleep(1)
        
        logger.info("=" * 70)
        logger.info("2단계: 텍스트 전체 선택 (Ctrl+A)")
        logger.info("=" * 70)
        
        # 텍스트 전체 선택
        await page.keyboard.press("Meta+A")  # macOS
        await asyncio.sleep(1)
        
        # 동적 툴바 분석
        logger.info("=" * 70)
        logger.info("3단계: 동적 서식 툴바 분석")
        logger.info("=" * 70)
        
        toolbar_info = await page.evaluate('''
            () => {
                const results = {
                    inlineToolbar: null,
                    textToolbar: null,
                    floatingToolbar: null,
                    allButtons: [],
                    strikeCandidate: null
                };
                
                // 1. 인라인 텍스트 툴바 찾기
                const inlineToolbar = document.querySelector('.se-inline-text-toolbar');
                if (inlineToolbar) {
                    results.inlineToolbar = {
                        class: inlineToolbar.className,
                        visible: inlineToolbar.offsetParent !== null,
                        buttons: []
                    };
                    
                    const buttons = inlineToolbar.querySelectorAll('button');
                    buttons.forEach((btn, idx) => {
                        const info = {
                            index: idx,
                            className: btn.className,
                            dataName: btn.getAttribute('data-name'),
                            ariaLabel: btn.getAttribute('aria-label'),
                            ariaPressed: btn.getAttribute('aria-pressed'),
                            title: btn.title,
                            innerText: btn.innerText.trim().substring(0, 30)
                        };
                        
                        // 취소선 버튼 후보 확인
                        const dn = (info.dataName || '').toLowerCase();
                        const al = (info.ariaLabel || '').toLowerCase();
                        const cn = (info.className || '').toLowerCase();
                        
                        if (dn.includes('strike') || dn.includes('line-through') ||
                            al.includes('strike') || al.includes('취소') ||
                            cn.includes('strike')) {
                            info.isStrikeCandidate = true;
                            results.strikeCandidate = info;
                        }
                        
                        results.inlineToolbar.buttons.push(info);
                    });
                }
                
                // 2. 다른 텍스트 툴바 패턴들 찾기
                const otherToolbars = [
                    '.se-text-toolbar',
                    '.se-toolbar-section-text',
                    '.se-popup-toolbar',
                    '.se-floating-toolbar',
                    '[class*="text-toolbar"]',
                    '[class*="inline-toolbar"]'
                ];
                
                otherToolbars.forEach(sel => {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {
                        results.textToolbar = {
                            selector: sel,
                            class: el.className,
                            buttonCount: el.querySelectorAll('button').length
                        };
                    }
                });
                
                // 3. 모든 활성화된 서식 버튼 검색
                const allFormatButtons = document.querySelectorAll(
                    'button[data-name*="bold"], button[data-name*="italic"], ' +
                    'button[data-name*="underline"], button[data-name*="strike"], ' +
                    'button[data-name*="text"]'
                );
                
                allFormatButtons.forEach((btn, idx) => {
                    if (btn.offsetParent !== null) {
                        results.allButtons.push({
                            index: idx,
                            dataName: btn.getAttribute('data-name'),
                            className: btn.className.substring(0, 100),
                            isVisible: true,
                            parentClass: btn.parentElement?.className?.substring(0, 50)
                        });
                    }
                });
                
                return results;
            }
        ''')
        
        logger.info(f"인라인 툴바: {toolbar_info.get('inlineToolbar')}")
        logger.info(f"텍스트 툴바: {toolbar_info.get('textToolbar')}")
        logger.info(f"취소선 후보: {toolbar_info.get('strikeCandidate')}")
        
        if toolbar_info.get('inlineToolbar'):
            logger.info("\n인라인 툴바 버튼 목록:")
            for btn in toolbar_info['inlineToolbar']['buttons']:
                logger.info(f"  [{btn['index']}] data-name={btn.get('dataName')}, class={btn.get('className')[:50]}")
        
        logger.info("=" * 70)
        logger.info("4단계: 취소선 버튼 활성화 테스트")
        logger.info("=" * 70)
        
        # 취소선 버튼 찾아서 클릭
        strike_result = await page.evaluate('''
            () => {
                // 인라인 툴바에서 취소선 버튼 찾기
                const inlineToolbar = document.querySelector('.se-inline-text-toolbar');
                if (!inlineToolbar) {
                    return { error: '인라인 툴바 없음' };
                }
                
                const buttons = inlineToolbar.querySelectorAll('button');
                let strikeBtn = null;
                let strikeBtnInfo = null;
                
                // data-name으로 취소선 버튼 찾기
                for (let i = 0; i < buttons.length; i++) {
                    const btn = buttons[i];
                    const dataName = (btn.getAttribute('data-name') || '').toLowerCase();
                    
                    if (dataName.includes('strike') || dataName === 'strikethrough' ||
                        dataName === 'strike' || dataName === 'line-through') {
                        strikeBtn = btn;
                        strikeBtnInfo = {
                            found: true,
                            index: i,
                            dataName: btn.getAttribute('data-name'),
                            className: btn.className,
                            beforeClick: {
                                ariaPressed: btn.getAttribute('aria-pressed'),
                                hasActiveClass: btn.classList.contains('active') ||
                                               btn.parentElement?.classList.contains('se-toolbar-button-active')
                            }
                        };
                        break;
                    }
                }
                
                // 못 찾으면 순서로 추정 (보통 4번째: B, I, U, S)
                if (!strikeBtn && buttons.length > 3) {
                    // 굵게, 기울임, 밑줄, 취소선 순서로 가정
                    // 하지만 먼저 버튼 순서 확인
                    let boldIdx = -1, italicIdx = -1, underlineIdx = -1;
                    
                    for (let i = 0; i < buttons.length; i++) {
                        const dn = (buttons[i].getAttribute('data-name') || '').toLowerCase();
                        if (dn === 'bold') boldIdx = i;
                        if (dn === 'italic') italicIdx = i;
                        if (dn === 'underline') underlineIdx = i;
                    }
                    
                    // 밑줄 다음 버튼이 취소선일 가능성
                    if (underlineIdx >= 0 && buttons.length > underlineIdx + 1) {
                        strikeBtn = buttons[underlineIdx + 1];
                        strikeBtnInfo = {
                            found: true,
                            guessed: true,
                            index: underlineIdx + 1,
                            dataName: strikeBtn.getAttribute('data-name'),
                            className: strikeBtn.className
                        };
                    }
                }
                
                if (!strikeBtn) {
                    return { error: '취소선 버튼 찾지 못함', buttonCount: buttons.length };
                }
                
                // 클릭하여 활성화
                strikeBtn.click();
                
                // 클릭 후 상태
                strikeBtnInfo.afterClick = {
                    ariaPressed: strikeBtn.getAttribute('aria-pressed'),
                    hasActiveClass: strikeBtn.classList.contains('active') ||
                                   strikeBtn.parentElement?.classList.contains('se-toolbar-button-active')
                };
                
                return strikeBtnInfo;
            }
        ''')
        
        logger.info(f"취소선 버튼 결과: {strike_result}")
        
        await asyncio.sleep(2)
        
        # 활성화 후 상태 재확인
        logger.info("=" * 70)
        logger.info("5단계: 활성화 상태 확인")
        logger.info("=" * 70)
        
        active_state = await page.evaluate('''
            () => {
                const inlineToolbar = document.querySelector('.se-inline-text-toolbar');
                if (!inlineToolbar) return { error: '인라인 툴바 없음' };
                
                const buttons = inlineToolbar.querySelectorAll('button');
                const result = { activeButtons: [], svgColors: [] };
                
                buttons.forEach((btn, idx) => {
                    const wrapper = btn.closest('.se-toolbar-button-wrapper');
                    const isActive = wrapper?.classList.contains('se-toolbar-button-active') ||
                                    btn.getAttribute('aria-pressed') === 'true' ||
                                    btn.classList.contains('active');
                    
                    if (isActive) {
                        result.activeButtons.push({
                            index: idx,
                            dataName: btn.getAttribute('data-name'),
                            wrapperClass: wrapper?.className,
                            ariaPressed: btn.getAttribute('aria-pressed')
                        });
                    }
                    
                    // SVG 색상 확인
                    const svg = btn.querySelector('svg');
                    if (svg) {
                        const paths = svg.querySelectorAll('path');
                        paths.forEach(path => {
                            const fill = path.getAttribute('fill');
                            if (fill && fill !== 'none' && fill !== '#555' && fill !== '#000') {
                                result.svgColors.push({
                                    btnIndex: idx,
                                    dataName: btn.getAttribute('data-name'),
                                    fill: fill
                                });
                            }
                        });
                    }
                });
                
                return result;
            }
        ''')
        
        logger.info(f"활성화된 버튼: {active_state.get('activeButtons')}")
        logger.info(f"SVG 색상: {active_state.get('svgColors')}")
        
        logger.info("=" * 70)
        logger.info("분석 완료! 10초 후 종료됩니다.")
        logger.info("=" * 70)
        
        await asyncio.sleep(10)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_inline_toolbar())
