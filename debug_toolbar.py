"""
네이버 스마트에디터 툴바 분석 스크립트
- 실제 취소선 버튼의 HTML 구조 파악
- 버튼 활성화 상태 감지 방법 확인
- 정확한 셀렉터 도출
"""

import asyncio
import json
from patchright.async_api import async_playwright
from security.session_manager import SecureSessionManager
from loguru import logger


async def analyze_toolbar():
    """네이버 스마트에디터 툴바 분석"""

    naver_id = "wncksdid0750"
    session_name = f"{naver_id}_clipboard"
    session_manager = SecureSessionManager()

    # 세션 로드
    storage_state = session_manager.load_session(session_name)
    if not storage_state:
        logger.error(f"세션을 찾을 수 없습니다: {session_name}")
        return

    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )

    context = await browser.new_context(
        storage_state=storage_state,
        viewport={'width': 1920, 'height': 1080},
        locale='ko-KR'
    )

    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    page = await context.new_page()

    try:
        # 글쓰기 페이지로 이동
        write_url = f"https://blog.naver.com/{naver_id}/postwrite"
        logger.info(f"글쓰기 페이지로 이동: {write_url}")
        await page.goto(write_url, wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # 팝업 처리
        try:
            cancel_btn = page.locator('button:has-text("취소")').first
            if await cancel_btn.is_visible(timeout=1000):
                await cancel_btn.click()
                logger.info("팝업 닫음")
        except:
            pass

        await asyncio.sleep(2)

        # ═══════════════════════════════════════════════════════════════
        # 1단계: 툴바 전체 구조 분석
        # ═══════════════════════════════════════════════════════════════

        logger.info("\n" + "═" * 70)
        logger.info("1단계: 툴바 전체 구조 분석")
        logger.info("═" * 70)

        toolbar_analysis = await page.evaluate('''
            () => {
                const toolbar = document.querySelector('.se-toolbar');
                if (!toolbar) return { error: '툴바를 찾을 수 없음' };

                const result = {
                    toolbarClass: toolbar.className,
                    toolbarChildren: [],
                    allButtons: []
                };

                // 툴바의 직계 자식들 분석
                const children = toolbar.children;
                for (const child of children) {
                    result.toolbarChildren.push({
                        tag: child.tagName,
                        className: child.className,
                        childCount: child.children.length
                    });
                }

                // 모든 버튼 분석
                const buttons = toolbar.querySelectorAll('button');
                let idx = 0;
                for (const btn of buttons) {
                    const parent = btn.parentElement;
                    const wrapper = btn.closest('.se-toolbar-button');

                    const btnInfo = {
                        index: idx++,
                        // 버튼 자체 정보
                        className: btn.className,
                        dataName: btn.getAttribute('data-name'),
                        ariaLabel: btn.getAttribute('aria-label'),
                        ariaPressed: btn.getAttribute('aria-pressed'),
                        title: btn.title,
                        type: btn.type,
                        // 부모 정보
                        parentClass: parent ? parent.className : null,
                        parentTag: parent ? parent.tagName : null,
                        // Wrapper 정보 (se-toolbar-button)
                        wrapperClass: wrapper ? wrapper.className : null,
                        // SVG 정보
                        hasSvg: !!btn.querySelector('svg'),
                        svgClass: btn.querySelector('svg')?.getAttribute('class'),
                        // 버튼 텍스트
                        innerText: btn.innerText?.trim().substring(0, 50)
                    };

                    result.allButtons.push(btnInfo);
                }

                return result;
            }
        ''')

        if toolbar_analysis.get('error'):
            logger.error(f"오류: {toolbar_analysis['error']}")
            return

        logger.info(f"툴바 클래스: {toolbar_analysis['toolbarClass']}")
        logger.info(f"버튼 개수: {len(toolbar_analysis['allButtons'])}")

        # ═══════════════════════════════════════════════════════════════
        # 2단계: 서식 버튼들 상세 분석 (굵게, 기울임, 밑줄, 취소선)
        # ═══════════════════════════════════════════════════════════════

        logger.info("\n" + "═" * 70)
        logger.info("2단계: 서식 관련 버튼 상세 분석")
        logger.info("═" * 70)

        # 서식 버튼으로 추정되는 것들 필터링
        format_keywords = ['bold', 'italic', 'underline', 'strike',
                          '굵게', '기울임', '밑줄', '취소선',
                          'B', 'I', 'U', 'S']

        for btn in toolbar_analysis['allButtons']:
            # 버튼 정보 중에 서식 관련 키워드가 있는지 확인
            btn_str = json.dumps(btn, ensure_ascii=False).lower()
            is_format = any(kw.lower() in btn_str for kw in format_keywords)

            if is_format:
                logger.info(f"\n버튼 #{btn['index']}: (서식 버튼으로 추정)")
                logger.info(f"  - className: {btn['className']}")
                logger.info(f"  - data-name: {btn['dataName']}")
                logger.info(f"  - aria-label: {btn['ariaLabel']}")
                logger.info(f"  - aria-pressed: {btn['ariaPressed']}")
                logger.info(f"  - title: {btn['title']}")
                logger.info(f"  - parentClass: {btn['parentClass']}")
                logger.info(f"  - wrapperClass: {btn['wrapperClass']}")
                logger.info(f"  - SVG: {btn['hasSvg']}, class={btn['svgClass']}")

        # ═══════════════════════════════════════════════════════════════
        # 3단계: 본문 클릭 후 취소선 버튼 클릭하여 활성화 상태 확인
        # ═══════════════════════════════════════════════════════════════

        logger.info("\n" + "═" * 70)
        logger.info("3단계: 취소선 버튼 클릭 전후 상태 비교")
        logger.info("═" * 70)

        # 본문 영역 클릭
        try:
            content_el = page.locator('.se-section-text p').first
            if await content_el.is_visible(timeout=2000):
                await content_el.click()
                await asyncio.sleep(0.5)
                logger.info("본문 영역 클릭 완료")
        except:
            pass

        # 클릭 전 상태
        before_state = await page.evaluate('''
            () => {
                const toolbar = document.querySelector('.se-toolbar');
                if (!toolbar) return [];

                const buttons = toolbar.querySelectorAll('button');
                const states = [];

                for (const btn of buttons) {
                    const wrapper = btn.closest('.se-toolbar-button') || btn.parentElement;
                    states.push({
                        ariaPressed: btn.getAttribute('aria-pressed'),
                        className: btn.className,
                        wrapperClass: wrapper?.className,
                        computedBg: window.getComputedStyle(btn).backgroundColor,
                        svgFill: btn.querySelector('svg')?.style?.fill ||
                                 btn.querySelector('svg path')?.getAttribute('fill'),
                        svgComputedFill: btn.querySelector('svg') ?
                                        window.getComputedStyle(btn.querySelector('svg')).fill : null
                    });
                }

                return states;
            }
        ''')

        # 취소선 버튼이 있을 법한 위치의 버튼들 클릭 테스트
        # 보통 서식 버튼들은 앞쪽에 위치 (굵게, 기울임, 밑줄, 취소선 순)

        # 추정 위치에서 클릭 시도 (일반적으로 3-6번째 버튼 근처)
        logger.info("\n버튼 순차 클릭 테스트 (서식 버튼 찾기)...")

        format_button_candidates = await page.evaluate('''
            () => {
                const toolbar = document.querySelector('.se-toolbar');
                if (!toolbar) return [];

                // 모든 버튼 중 서식 그룹에 속한 것으로 보이는 버튼들 찾기
                const allButtons = toolbar.querySelectorAll('button');
                const candidates = [];

                // 버튼 그룹 분석 - 인접한 버튼들을 그룹으로
                let currentGroup = [];
                let prevRight = 0;

                for (let i = 0; i < allButtons.length; i++) {
                    const btn = allButtons[i];
                    const rect = btn.getBoundingClientRect();
                    const wrapper = btn.closest('.se-toolbar-button') || btn.parentElement;

                    // 서식 버튼 특징: 아이콘만 있고 텍스트 없음, SVG 있음
                    const hasSvg = !!btn.querySelector('svg');
                    const hasOnlyIcon = btn.innerText.trim() === '' && hasSvg;

                    if (hasOnlyIcon) {
                        candidates.push({
                            index: i,
                            left: rect.left,
                            wrapperClass: wrapper?.className,
                            ariaLabel: btn.getAttribute('aria-label'),
                            dataName: btn.getAttribute('data-name'),
                            // SVG 내용 분석
                            svgPaths: btn.querySelector('svg')?.querySelectorAll('path')?.length || 0,
                            svgViewBox: btn.querySelector('svg')?.getAttribute('viewBox')
                        });
                    }
                }

                return candidates;
            }
        ''')

        logger.info(f"\n아이콘 버튼 후보 {len(format_button_candidates)}개 발견:")
        for cand in format_button_candidates[:10]:  # 처음 10개만 출력
            logger.info(f"  #{cand['index']}: aria-label={cand.get('ariaLabel')}, "
                       f"data-name={cand.get('dataName')}, wrapper={cand.get('wrapperClass')}")

        # ═══════════════════════════════════════════════════════════════
        # 4단계: 각 버튼 클릭 시 변화 관찰 (서식 버튼 식별)
        # ═══════════════════════════════════════════════════════════════

        logger.info("\n" + "═" * 70)
        logger.info("4단계: 버튼 클릭 시 상태 변화 관찰")
        logger.info("═" * 70)

        # 처음 10개 아이콘 버튼에 대해 클릭 테스트
        test_indices = [c['index'] for c in format_button_candidates[:10]]

        for btn_idx in test_indices:
            # 클릭 전 상태 저장
            before = await page.evaluate('''
                (idx) => {
                    const toolbar = document.querySelector('.se-toolbar');
                    const btn = toolbar.querySelectorAll('button')[idx];
                    if (!btn) return null;

                    const wrapper = btn.closest('.se-toolbar-button') || btn.parentElement;
                    return {
                        ariaPressed: btn.getAttribute('aria-pressed'),
                        btnClass: btn.className,
                        wrapperClass: wrapper?.className
                    };
                }
            ''', btn_idx)

            if not before:
                continue

            # 버튼 클릭
            clicked = await page.evaluate('''
                (idx) => {
                    const toolbar = document.querySelector('.se-toolbar');
                    const btn = toolbar.querySelectorAll('button')[idx];
                    if (!btn) return false;
                    btn.click();
                    return true;
                }
            ''', btn_idx)

            await asyncio.sleep(0.3)

            # 클릭 후 상태 확인
            after = await page.evaluate('''
                (idx) => {
                    const toolbar = document.querySelector('.se-toolbar');
                    const btn = toolbar.querySelectorAll('button')[idx];
                    if (!btn) return null;

                    const wrapper = btn.closest('.se-toolbar-button') || btn.parentElement;
                    return {
                        ariaPressed: btn.getAttribute('aria-pressed'),
                        btnClass: btn.className,
                        wrapperClass: wrapper?.className
                    };
                }
            ''', btn_idx)

            if not after:
                continue

            # 상태 변화 감지
            changes = []
            if before['ariaPressed'] != after['ariaPressed']:
                changes.append(f"aria-pressed: {before['ariaPressed']} → {after['ariaPressed']}")
            if before['btnClass'] != after['btnClass']:
                changes.append(f"btnClass 변화 있음")
            if before['wrapperClass'] != after['wrapperClass']:
                changes.append(f"wrapperClass: {before['wrapperClass']} → {after['wrapperClass']}")

            if changes:
                logger.info(f"\n버튼 #{btn_idx} 클릭 시 상태 변화:")
                for change in changes:
                    logger.info(f"  - {change}")

                # 다시 클릭하여 원상복구
                await page.evaluate('''
                    (idx) => {
                        const toolbar = document.querySelector('.se-toolbar');
                        const btn = toolbar.querySelectorAll('button')[idx];
                        if (btn) btn.click();
                    }
                ''', btn_idx)
                await asyncio.sleep(0.2)

        # ═══════════════════════════════════════════════════════════════
        # 5단계: 최종 결과 - 취소선 버튼 식별
        # ═══════════════════════════════════════════════════════════════

        logger.info("\n" + "═" * 70)
        logger.info("5단계: 최종 분석 결과")
        logger.info("═" * 70)

        final_analysis = await page.evaluate('''
            () => {
                const toolbar = document.querySelector('.se-toolbar');
                if (!toolbar) return { error: '툴바 없음' };

                const buttons = toolbar.querySelectorAll('button');
                const results = [];

                // 서식 버튼 그룹 찾기 (보통 연속된 4개: 굵게, 기울임, 밑줄, 취소선)
                for (let i = 0; i < buttons.length; i++) {
                    const btn = buttons[i];
                    const svg = btn.querySelector('svg');
                    if (!svg) continue;

                    // SVG 내용으로 버튼 종류 추측
                    const paths = svg.querySelectorAll('path');
                    const pathData = [];
                    paths.forEach(p => pathData.push(p.getAttribute('d')?.substring(0, 30)));

                    const wrapper = btn.closest('.se-toolbar-button') || btn.parentElement;

                    results.push({
                        index: i,
                        wrapperClass: wrapper?.className,
                        pathCount: paths.length,
                        pathSample: pathData.slice(0, 2)
                    });
                }

                // 활성화 감지 방법 분석
                const activeDetection = {
                    // 가장 흔한 패턴들
                    patterns: [
                        "wrapper에 'se-toolbar-button-active' 클래스",
                        "aria-pressed='true' 속성",
                        "버튼 클래스에 'active' 포함",
                        "SVG fill 색상 변화"
                    ]
                };

                return {
                    iconButtons: results,
                    activeDetection: activeDetection
                };
            }
        ''')

        logger.info("\n아이콘 버튼 목록 (처음 15개):")
        for btn in final_analysis.get('iconButtons', [])[:15]:
            logger.info(f"  #{btn['index']}: wrapper={btn['wrapperClass']}, paths={btn['pathCount']}")

        logger.info("\n활성화 감지 패턴 후보:")
        for pattern in final_analysis.get('activeDetection', {}).get('patterns', []):
            logger.info(f"  - {pattern}")

        # 브라우저 대기 (사용자가 직접 확인할 수 있도록)
        logger.info("\n" + "═" * 70)
        logger.info("분석 완료! 브라우저에서 직접 확인하세요.")
        logger.info("개발자 도구(F12)에서 취소선 버튼을 직접 검사할 수 있습니다.")
        logger.info("종료하려면 Enter 키를 누르세요...")
        logger.info("═" * 70)

        input()  # 사용자 입력 대기

    except Exception as e:
        logger.error(f"분석 중 오류: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(analyze_toolbar())
