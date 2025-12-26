"""
Visual Designer Agent
- Vertex AI Imagen 3를 통한 고품질 이미지 생성 (우선)
- Pillow를 통한 이미지 합성 및 텍스트 오버레이 (폴백)
- 3가지 타입: 썸네일, 수익 인증, 시장 차트
"""

import os
import io
import random
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import google.generativeai as genai
from loguru import logger

from security.credential_manager import CredentialManager

# Gemini 이미지 생성기 import (utils에서)
try:
    from utils.gemini_image import GeminiImageGenerator
    GEMINI_IMAGE_AVAILABLE = True
except ImportError:
    GEMINI_IMAGE_AVAILABLE = False


class VisualAgent:
    """컨텍스트 기반 이미지 생성 및 합성 에이전트"""

    IMAGE_TYPES = ["thumbnail", "proof", "chart"]

    def __init__(
        self,
        credential_manager: Optional[CredentialManager] = None,
        output_dir: str = "./generated_images",
        use_gemini_image: bool = True
    ):
        """
        Args:
            credential_manager: 자격증명 관리자
            output_dir: 이미지 저장 디렉토리
            use_gemini_image: Gemini Imagen 사용 여부 (False면 Pillow 폴백)
        """
        self.cred_manager = credential_manager or CredentialManager()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Gemini 이미지 생성기 초기화 (Imagen 4.0)
        self.gemini_image = None
        if use_gemini_image and GEMINI_IMAGE_AVAILABLE:
            try:
                self.gemini_image = GeminiImageGenerator()
                logger.success("Gemini Imagen 4.0 초기화 완료")
            except Exception as e:
                logger.warning(f"Gemini 이미지 생성기 초기화 실패: {e}, Pillow 폴백 사용")
                self.gemini_image = None

        # Gemini Pro API 설정 (텍스트 분석용)
        google_key = self.cred_manager.get_api_key("google")
        if google_key:
            genai.configure(api_key=google_key)
            self.gemini = genai.GenerativeModel('gemini-1.5-pro')
        else:
            self.gemini = None

    def generate_images(
        self,
        post_title: str,
        post_content: str,
        sentiment: str = "neutral",
        image_prompts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[str]]:
        """
        블로그 포스트용 이미지 세트 생성

        Args:
            post_title: 포스트 제목
            post_content: 포스트 본문
            sentiment: 감성 (positive/negative/neutral)
            image_prompts: Claude가 생성한 이미지 프롬프트 (Imagen 3용)
                {
                    "thumbnail_prompt": str,
                    "content_prompts": List[str],
                    "style_guide": str
                }

        Returns:
            {
                "thumbnail": [path],     # 썸네일 이미지
                "content": [path, ...],  # 본문 이미지들
                "proof": [path],         # 수익 인증 이미지 (Pillow)
                "chart": [path]          # 차트 이미지 (Pillow)
            }
        """
        logger.info("이미지 생성 시작")

        result = {
            "thumbnail": [],
            "content": [],
            "proof": [],
            "chart": []
        }

        # Gemini Imagen이 사용 가능하고 프롬프트가 있으면 Imagen 사용
        if self.gemini_image and image_prompts:
            logger.info("Gemini Imagen 4.0으로 이미지 생성 중...")
            try:
                # 썸네일 생성
                thumbnail_prompt = image_prompts.get("thumbnail_prompt", "")
                if thumbnail_prompt:
                    thumb_path = self.gemini_image.generate_image(
                        prompt=thumbnail_prompt,
                        style="digital-art"
                    )
                    if thumb_path:
                        result["thumbnail"].append(thumb_path)

                # 본문 이미지 생성
                for prompt in image_prompts.get("content_prompts", []):
                    content_path = self.gemini_image.generate_image(
                        prompt=prompt,
                        style="digital-art"
                    )
                    if content_path:
                        result["content"].append(content_path)

                if result["thumbnail"] or result["content"]:
                    logger.success(f"Imagen 이미지 생성 완료: 썸네일 {len(result['thumbnail'])}개, 본문 {len(result['content'])}개")
                else:
                    logger.warning("Imagen 이미지 생성 실패, Pillow 폴백 사용")
                    self._generate_pillow_fallback(result, post_title, sentiment)

            except Exception as e:
                logger.error(f"Imagen 오류: {e}, Pillow 폴백 사용")
                self._generate_pillow_fallback(result, post_title, sentiment)
        else:
            # Pillow 폴백
            logger.info("Pillow로 이미지 생성 중...")
            self._generate_pillow_fallback(result, post_title, sentiment)

        return result

    def _generate_pillow_fallback(
        self,
        result: Dict[str, List[str]],
        post_title: str,
        sentiment: str
    ) -> None:
        """Pillow 기반 폴백 이미지 생성"""
        try:
            # 1. 썸네일 생성
            if not result["thumbnail"]:
                thumbnail_path = self.create_thumbnail(post_title, sentiment)
                if thumbnail_path:
                    result["thumbnail"].append(thumbnail_path)

            # 2. 수익 인증 이미지 생성 (합성)
            proof_path = self.create_proof_image(sentiment)
            if proof_path:
                result["proof"].append(proof_path)

            # 3. 차트 이미지 생성
            chart_path = self.create_chart_image(post_title, sentiment)
            if chart_path:
                result["chart"].append(chart_path)

            logger.success(f"Pillow 이미지 생성 완료: {sum(len(v) for v in result.values())}개")

        except Exception as e:
            logger.error(f"Pillow 이미지 생성 중 오류: {e}")

    def create_thumbnail(
        self,
        title: str,
        sentiment: str = "neutral"
    ) -> Optional[str]:
        """
        썸네일 이미지 생성

        Args:
            title: 제목
            sentiment: 감성

        Returns:
            이미지 파일 경로
        """
        try:
            # 이미지 생성 (800x600)
            img = self._create_base_image(800, 600, sentiment)

            # 제목 텍스트 오버레이
            img_with_text = self._add_title_overlay(img, title)

            # 저장
            filename = f"thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self.output_dir / filename
            img_with_text.save(filepath, "JPEG", quality=90)

            logger.info(f"썸네일 생성: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"썸네일 생성 실패: {e}")
            return None

    def create_proof_image(self, sentiment: str = "neutral") -> Optional[str]:
        """
        수익 인증 이미지 생성 (AI 대시보드 + 수익률 합성)

        Args:
            sentiment: 감성 (양수/음수 수익률 결정)

        Returns:
            이미지 파일 경로
        """
        try:
            # 베이스 대시보드 이미지 생성
            dashboard = self._create_dashboard_base(600, 400)

            # 수익률 데이터 생성
            profit_data = self._generate_profit_data(sentiment)

            # 데이터 오버레이
            img_with_data = self._add_profit_overlay(dashboard, profit_data)

            # 스마트폰 프레임 추가
            img_with_frame = self._add_phone_frame(img_with_data)

            # 저장
            filename = f"proof_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self.output_dir / filename
            img_with_frame.save(filepath, "JPEG", quality=85)

            logger.info(f"수익 인증 이미지 생성: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"수익 인증 이미지 생성 실패: {e}")
            return None

    def create_chart_image(
        self,
        title: str,
        sentiment: str = "neutral"
    ) -> Optional[str]:
        """
        시장 차트 이미지 생성

        Args:
            title: 차트 제목
            sentiment: 감성 (상승/하락 차트)

        Returns:
            이미지 파일 경로
        """
        try:
            # 간단한 차트 이미지 생성
            chart = self._create_simple_chart(700, 400, sentiment)

            # 제목 추가
            chart_with_title = self._add_chart_title(chart, title)

            # 저장
            filename = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self.output_dir / filename
            chart_with_title.save(filepath, "JPEG", quality=90)

            logger.info(f"차트 이미지 생성: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"차트 이미지 생성 실패: {e}")
            return None

    # ============================================
    # 이미지 생성 헬퍼 메서드
    # ============================================

    def _create_base_image(
        self,
        width: int,
        height: int,
        sentiment: str
    ) -> Image.Image:
        """기본 그라데이션 배경 이미지 생성"""

        # 감성에 따른 색상
        if sentiment == "positive":
            color1 = (30, 144, 255)   # 파란색
            color2 = (50, 205, 50)    # 초록색
        elif sentiment == "negative":
            color1 = (220, 20, 60)    # 빨간색
            color2 = (139, 0, 139)    # 자주색
        else:
            color1 = (70, 130, 180)   # 스틸 블루
            color2 = (100, 149, 237)  # 코른플라워 블루

        # 그라데이션 생성
        img = Image.new("RGB", (width, height), color1)
        draw = ImageDraw.Draw(img)

        for i in range(height):
            ratio = i / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(0, i), (width, i)], fill=(r, g, b))

        # 약간의 노이즈 추가 (자연스러움)
        return img.filter(ImageFilter.GaussianBlur(radius=2))

    def _add_title_overlay(
        self,
        img: Image.Image,
        title: str
    ) -> Image.Image:
        """제목 텍스트 오버레이"""

        # 복사본 생성
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)

        # 폰트 (시스템 폰트 사용)
        try:
            # macOS/Windows 기본 폰트
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 48)
        except:
            font = ImageFont.load_default()

        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 중앙 배치
        x = (img.width - text_width) // 2
        y = (img.height - text_height) // 2

        # 텍스트 배경 (반투명 검은색)
        padding = 20
        draw.rectangle(
            [
                x - padding,
                y - padding,
                x + text_width + padding,
                y + text_height + padding
            ],
            fill=(0, 0, 0, 180)
        )

        # 텍스트 (흰색)
        draw.text((x, y), title, font=font, fill=(255, 255, 255))

        return img_copy

    def _create_dashboard_base(self, width: int, height: int) -> Image.Image:
        """대시보드 베이스 이미지"""

        # 어두운 배경 (대시보드 느낌)
        img = Image.new("RGB", (width, height), (30, 30, 40))
        draw = ImageDraw.Draw(img)

        # 그리드 라인
        grid_color = (50, 50, 60)
        for i in range(0, width, 50):
            draw.line([(i, 0), (i, height)], fill=grid_color, width=1)
        for i in range(0, height, 50):
            draw.line([(0, i), (width, i)], fill=grid_color, width=1)

        return img

    def _generate_profit_data(self, sentiment: str) -> Dict[str, Any]:
        """가상 수익률 데이터 생성"""

        if sentiment == "positive":
            profit = round(random.uniform(3.5, 12.8), 2)
        elif sentiment == "negative":
            profit = round(random.uniform(-8.5, -1.2), 2)
        else:
            profit = round(random.uniform(-2.0, 5.0), 2)

        return {
            "profit_percent": profit,
            "trades": random.randint(15, 45),
            "win_rate": round(random.uniform(55, 75), 1)
        }

    def _add_profit_overlay(
        self,
        img: Image.Image,
        data: Dict[str, Any]
    ) -> Image.Image:
        """수익률 데이터 오버레이"""

        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)

        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 36)
            font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 20)
        except:
            font_large = font_small = ImageFont.load_default()

        # 수익률 (중앙 상단)
        profit_text = f"{data['profit_percent']:+.2f}%"
        profit_color = (50, 205, 50) if data['profit_percent'] > 0 else (220, 20, 60)

        bbox = draw.textbbox((0, 0), profit_text, font=font_large)
        x = (img.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 40), profit_text, font=font_large, fill=profit_color)

        # 거래 횟수 및 승률
        info_y = img.height - 100
        draw.text((50, info_y), f"거래: {data['trades']}회", font=font_small, fill=(200, 200, 200))
        draw.text((50, info_y + 30), f"승률: {data['win_rate']}%", font=font_small, fill=(200, 200, 200))

        return img_copy

    def _add_phone_frame(self, img: Image.Image) -> Image.Image:
        """스마트폰 프레임 추가"""

        # 프레임 크기 (이미지보다 약간 크게)
        frame_width = img.width + 40
        frame_height = img.height + 100

        # 프레임 이미지 생성
        frame = Image.new("RGB", (frame_width, frame_height), (20, 20, 20))

        # 이미지를 프레임 중앙에 배치
        offset_x = (frame_width - img.width) // 2
        offset_y = (frame_height - img.height) // 2
        frame.paste(img, (offset_x, offset_y))

        # 상단 노치 그리기
        draw = ImageDraw.Draw(frame)
        notch_width = 150
        notch_height = 30
        notch_x = (frame_width - notch_width) // 2
        draw.rectangle(
            [notch_x, 0, notch_x + notch_width, notch_height],
            fill=(10, 10, 10)
        )

        return frame

    def _create_simple_chart(
        self,
        width: int,
        height: int,
        sentiment: str
    ) -> Image.Image:
        """간단한 차트 이미지 생성"""

        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # 차트 영역
        margin = 50
        chart_x = margin
        chart_y = margin
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        # 축 그리기
        draw.line(
            [(chart_x, chart_y + chart_height), (chart_x + chart_width, chart_y + chart_height)],
            fill=(0, 0, 0), width=2
        )
        draw.line(
            [(chart_x, chart_y), (chart_x, chart_y + chart_height)],
            fill=(0, 0, 0), width=2
        )

        # 가상 데이터 포인트 생성
        points = []
        num_points = 20
        base_value = chart_height // 2

        for i in range(num_points):
            x = chart_x + (i * chart_width // (num_points - 1))

            # 감성에 따른 트렌드
            if sentiment == "positive":
                trend = -i * 5  # 상승
            elif sentiment == "negative":
                trend = i * 5   # 하락
            else:
                trend = 0

            y = chart_y + base_value + trend + random.randint(-30, 30)
            y = max(chart_y, min(chart_y + chart_height, y))
            points.append((x, y))

        # 라인 차트 그리기
        line_color = (50, 205, 50) if sentiment == "positive" else (220, 20, 60)
        draw.line(points, fill=line_color, width=3)

        # 포인트 마커
        for point in points:
            draw.ellipse(
                [point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4],
                fill=line_color
            )

        return img

    def _add_chart_title(self, img: Image.Image, title: str) -> Image.Image:
        """차트 제목 추가"""

        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 24)
        except:
            font = ImageFont.load_default()

        # 상단 중앙에 제목
        bbox = draw.textbbox((0, 0), title, font=font)
        x = (img.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 10), title, font=font, fill=(0, 0, 0))

        return img_copy


# ============================================
# 테스트 코드
# ============================================

def test_visual_agent():
    """Visual Agent 테스트"""
    print("\n=== Visual Agent 테스트 ===\n")

    agent = VisualAgent()

    result = agent.generate_images(
        post_title="비트코인 6만 달러 돌파!",
        post_content="시장이 활황입니다...",
        sentiment="positive"
    )

    print("생성된 이미지:")
    for img_type, paths in result.items():
        print(f"  {img_type}: {len(paths)}개")
        for path in paths:
            print(f"    - {path}")


if __name__ == "__main__":
    test_visual_agent()
