"""
Human Behavior Simulation
- 베지어 곡선 기반 마우스 이동
- 자연스러운 타이핑 리듬
- 랜덤 딜레이 및 휴식 시간
"""

import asyncio
import random
from typing import Tuple
from scipy.interpolate import interp1d
import numpy as np


class HumanBehavior:
    """인간 행동 패턴 시뮬레이션 클래스"""

    def __init__(
        self,
        typing_speed_min_ms: int = 80,
        typing_speed_max_ms: int = 180,
        use_bezier: bool = True
    ):
        """
        Args:
            typing_speed_min_ms: 최소 타이핑 속도 (밀리초)
            typing_speed_max_ms: 최대 타이핑 속도 (밀리초)
            use_bezier: 베지어 곡선 사용 여부
        """
        self.typing_speed_min = typing_speed_min_ms / 1000
        self.typing_speed_max = typing_speed_max_ms / 1000
        self.use_bezier = use_bezier

    async def random_delay(self, min_sec: float, max_sec: float):
        """랜덤 딜레이"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def human_type(self, page, selector: str, text: str):
        """
        인간처럼 타이핑

        Args:
            page: Playwright Page 객체
            selector: CSS 선택자
            text: 입력할 텍스트
        """
        await page.click(selector)
        await self.random_delay(0.1, 0.3)

        for char in text:
            await page.keyboard.type(char)

            # 타이핑 속도 (불규칙)
            delay = random.uniform(self.typing_speed_min, self.typing_speed_max)

            # 가끔 더 긴 pause (생각하는 시간)
            if random.random() < 0.1:  # 10% 확률
                delay *= random.uniform(2, 4)

            await asyncio.sleep(delay)

    async def human_click(self, page, selector: str):
        """인간처럼 클릭"""
        await page.click(selector)
        await self.random_delay(0.1, 0.3)

    def bezier_curve(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        control_points: int = 3
    ) -> list:
        """
        베지어 곡선 생성

        Args:
            start: 시작 좌표 (x, y)
            end: 끝 좌표 (x, y)
            control_points: 제어점 개수

        Returns:
            곡선 위의 점들 리스트
        """
        # 제어점 생성
        controls = []
        for i in range(control_points):
            t = (i + 1) / (control_points + 1)
            x = start[0] + (end[0] - start[0]) * t + random.uniform(-50, 50)
            y = start[1] + (end[1] - start[1]) * t + random.uniform(-50, 50)
            controls.append((x, y))

        # 모든 점 (시작 + 제어점 + 끝)
        all_points = [start] + controls + [end]

        # 베지어 곡선 계산
        n = len(all_points) - 1
        curve_points = []

        for t in np.linspace(0, 1, 50):
            x, y = 0, 0
            for i, (px, py) in enumerate(all_points):
                # 베르슈타인 다항식
                binomial = np.math.comb(n, i)
                term = binomial * (t ** i) * ((1 - t) ** (n - i))
                x += term * px
                y += term * py

            curve_points.append((int(x), int(y)))

        return curve_points


# 전역 인스턴스
default_human_behavior = HumanBehavior()
