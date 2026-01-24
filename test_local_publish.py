#!/usr/bin/env python3
"""로컬 환경 발행 테스트 - IP 차단 여부 확인용"""
import asyncio
import os
import sys
import time

# 환경 설정
os.environ['HEADLESS'] = 'False'  # GUI 모드

sys.path.insert(0, '/Users/mr.joo/Desktop/네이버블로그봇')

from loguru import logger
from auto_post import NaverBlogPoster

async def test_local_publish():
    """로컬 환경에서 발행 테스트"""
    logger.info('=' * 60)
    logger.info('🖥️ 로컬 환경 발행 테스트 시작')
    logger.info('=' * 60)
    logger.info(f'HEADLESS: {os.environ.get("HEADLESS")}')

    poster = NaverBlogPoster(naver_id='wncksdid0750')

    try:
        # 브라우저 시작 (GUI 모드)
        logger.info('🚀 브라우저 시작 중 (GUI 모드)...')
        await poster.start_browser()
        logger.success('✅ 브라우저 시작 완료')

        # 로그인 상태 확인
        logger.info('🔐 로그인 상태 확인 중...')
        await poster.check_login_status()
        logger.success('✅ 로그인 상태 확인 완료')

        # 간단한 테스트 포스트
        timestamp = int(time.time())
        test_title = f'로컬 테스트 포스트 {timestamp}'
        test_content = '''
<p>이것은 로컬 환경에서 작성된 테스트 포스트입니다.</p>
<p>서버 IP 차단 여부를 확인하기 위한 테스트입니다.</p>
<p>타임스탬프: ''' + str(timestamp) + '''</p>
'''

        logger.info(f'📝 제목: {test_title}')

        # 발행 시도
        result = await poster.post(
            title=test_title,
            content=test_content
        )

        if result and result.get('success'):
            logger.success('=' * 60)
            logger.success('🎉 로컬 환경 발행 성공!')
            logger.success(f'📎 URL: {result.get("url", "N/A")}')
            logger.success('=' * 60)
            logger.info('')
            logger.info('✅ 결론: 서버 IP가 네이버에 의해 차단되었습니다.')
            logger.info('   해결책: 다른 서버 IP 또는 Residential Proxy 사용')
        else:
            logger.error('=' * 60)
            logger.error('❌ 로컬에서도 발행 실패')
            logger.error(f'결과: {result}')
            logger.error('=' * 60)
            logger.info('')
            logger.info('⚠️ 결론: IP 문제가 아닌 다른 원인일 수 있습니다.')

    except Exception as e:
        logger.exception(f'❌ 예외 발생: {e}')
    finally:
        await poster.close_browser()

if __name__ == '__main__':
    asyncio.run(test_local_publish())
