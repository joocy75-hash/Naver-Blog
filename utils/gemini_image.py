"""
Gemini API를 사용한 이미지 생성 모듈
- Gemini 3.0 Flash Preview 모델 사용
- 블로그 포스트용 썸네일/삽입 이미지 생성
"""

import os
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai 패키지가 설치되지 않음. pip install google-genai")


class GeminiImageGenerator:
    """Gemini API 이미지 생성 클래스 (Gemini 2.0 Flash)"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Google API 키 (없으면 키체인에서 로드)
        """
        if not GENAI_AVAILABLE:
            raise ImportError("google-genai 패키지를 설치하세요: pip install google-genai")

        self.api_key = api_key or self._load_api_key()
        if not self.api_key:
            raise ValueError("Google API 키가 필요합니다")

        self.client = genai.Client(api_key=self.api_key)
        self.output_dir = Path("./generated_images")
        self.output_dir.mkdir(exist_ok=True)

        logger.info("Gemini 이미지 생성기 초기화 완료 (Gemini 3.0 Flash Preview)")

    def _load_api_key(self) -> Optional[str]:
        """키체인 또는 환경변수에서 API 키 로드"""
        # 1. 환경 변수
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            return api_key

        # 2. 키체인
        try:
            from security.credential_manager import CredentialManager
            manager = CredentialManager()
            api_key = manager.get_api_key("google")
            if api_key:
                return api_key
        except Exception as e:
            logger.debug(f"키체인 로드 실패: {e}")

        return None

    def generate_image(
        self,
        prompt: str,
        filename: Optional[str] = None,
        style: str = "digital-art"
    ) -> Optional[str]:
        """
        Gemini 2.0 Flash를 사용한 이미지 생성

        Args:
            prompt: 이미지 설명 (영어 권장)
            filename: 저장할 파일명 (없으면 자동 생성)
            style: 스타일 힌트

        Returns:
            생성된 이미지 파일 경로
        """
        logger.info(f"이미지 생성 중: {prompt[:50]}...")

        # 프롬프트 최적화
        enhanced_prompt = self._enhance_prompt(prompt, style)

        try:
            # Imagen 4.0 모델로 이미지 생성
            response = self.client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=enhanced_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    person_generation="DONT_ALLOW",
                )
            )

            # 이미지 저장
            if response.generated_images:
                image_data = response.generated_images[0].image.image_bytes

                if not filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"blog_image_{timestamp}.png"

                filepath = self.output_dir / filename
                filepath.write_bytes(image_data)

                logger.success(f"이미지 생성 완료: {filepath}")
                return str(filepath)

            logger.error("이미지 생성 결과 없음")
            return None

        except Exception as e:
            logger.error(f"이미지 생성 실패: {e}")
            # 상세 오류 출력
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """
        프롬프트 품질 향상 - 다양한 스타일 지원

        지원 스타일:
        - photo-realistic: 사실적인 사진
        - digital-art: 디지털 아트 (기본)
        - cyberpunk: 사이버펑크 네온
        - 3d-render: 3D 렌더링
        - isometric: 아이소메트릭 일러스트
        - flat-illustration: 플랫 일러스트
        - infographic: 인포그래픽
        - minimalist: 미니멀리즘
        - artistic: 예술적 일러스트
        - gradient-abstract: 그라데이션 추상화
        - futuristic: 미래지향적
        """
        # ═══════════════════════════════════════════════════════════════
        # 밈 기반 크립토 아트 스타일 수정자 (content_agent.py와 동기화)
        # ═══════════════════════════════════════════════════════════════
        style_modifiers = {
            # ★ 밈/크립토 아트 스타일 (최우선)
            "crypto-meme": "crypto meme art style, vibrant neon colors, bold composition, dramatic lighting, high contrast, cartoon character, explosive energy",
            "cyberpunk": "cyberpunk aesthetic, neon glow, futuristic cityscape, dark background with vibrant neon colors, high contrast, holographic elements",
            "cinematic": "cinematic digital illustration, dramatic lighting, high contrast, volumetric lighting, movie poster quality, epic composition",
            "pixel-art": "8-bit pixel art style, retro gaming aesthetic, bold colors, nostalgic video game look, clean pixels",
            "3d-render": "cinematic 3D render, dramatic lighting, depth of field, volumetric lighting, high-end CGI quality, Pixar-like quality",

            # 밈 캐릭터 관련
            "meme-frog": "cartoon frog character, cool sunglasses, confident pose, neon lighting, crypto trading theme",
            "meme-doge": "Shiba Inu dog character, determined expression, space/rocket theme, vibrant colors",
            "meme-bull": "powerful cartoon bull character, suit and tie, victory pose, stock market theme, green colors",
            "meme-robot": "futuristic robot with glowing eyes, AI trading theme, holographic displays, blue neon",

            # 액션/상황 관련
            "rocket-moon": "rocket blasting off to the moon, explosive fire trail, space background, stars and Earth visible",
            "bull-run": "charging bull, breaking through barriers, green upward arrows, explosive energy, victory atmosphere",
            "trading-floor": "holographic trading screens, digital charts, futuristic financial district, neon data streams",

            # 기본 스타일 (폴백용)
            "photo-realistic": "hyper-realistic photograph, professional photography, high detail, studio lighting, 8K resolution",
            "digital-art": "digital art, modern design, clean lines, tech aesthetic, vector-like quality",
            "futuristic": "futuristic tech aesthetic, holographic elements, sleek metallic surfaces, blue and purple tones",
            "neon-glow": "neon glow effect, dark background, vibrant electric colors, light trails, cyberpunk mood",
        }

        # 스타일 매칭 - 부분 매칭 지원 (프롬프트에 스타일이 포함된 경우)
        modifier = None
        style_lower = style.lower()

        # 정확한 매칭 시도
        if style_lower in style_modifiers:
            modifier = style_modifiers[style_lower]
        else:
            # 부분 매칭 시도 (예: "cinematic 3D render" -> "3d-render")
            for key, value in style_modifiers.items():
                if key.replace("-", " ") in style_lower or key.replace("-", "") in style_lower:
                    modifier = value
                    break

        # 매칭 실패 시 프롬프트에 스타일 직접 포함
        if not modifier:
            # style 자체가 상세한 스타일 설명인 경우 그대로 사용
            if len(style) > 20:  # 긴 스타일 설명
                modifier = style
            else:
                # ★ 기본 스타일을 밈/크립토 아트로 변경
                modifier = style_modifiers["crypto-meme"]

        # 이미지 생성 명령어 포함 (밈 스타일 강조)
        enhanced = f"Generate an image: {prompt}. Style: {modifier}. Crypto meme art aesthetic, vibrant neon colors, dramatic lighting, high contrast. Professional quality, no text, no words, no letters, no watermarks, no human faces."

        return enhanced

    def generate_crypto_thumbnail(
        self,
        topic: str = "cryptocurrency market",
        mood: str = "neutral"  # bullish, bearish, neutral
    ) -> Optional[str]:
        """암호화폐 관련 밈 스타일 썸네일 생성 - 매번 다양한 조합"""
        import random

        # ═══════════════════════════════════════════════════════════════
        # 확장된 밈 캐릭터 풀 (15가지 이상) - 매번 다른 캐릭터!
        # ═══════════════════════════════════════════════════════════════
        characters = [
            # 클래식 밈 동물
            "a cool cartoon frog with laser eyes and diamond hands",
            "a Shiba Inu dog astronaut with a golden helmet",
            "a powerful muscular bull in a luxury suit smashing through walls",
            "a wise cartoon cat with glowing cyber eyes",
            "a determined cartoon gorilla with diamond fists",
            "a majestic lion king with a golden crown and neon mane",
            # 로봇/AI
            "a sleek humanoid robot trader with holographic brain",
            "a cute robot assistant with heart-shaped LED eyes",
            "a massive mech warrior with trading screens on armor",
            # 판타지
            "a powerful dragon breathing golden fire",
            "a phoenix rising from flames with golden wings",
            "a magical unicorn with rainbow neon mane",
            # 캐릭터
            "a mysterious hooded figure with glowing green eyes",
            "a samurai warrior with digital katana",
            "a viking warrior with crypto runes on shield",
            "a superhero with cape made of golden coins",
        ]

        # ═══════════════════════════════════════════════════════════════
        # 확장된 액션 풀 (감성별로 다양화)
        # ═══════════════════════════════════════════════════════════════
        actions = {
            "bullish": [
                "riding a blazing rocket to the moon",
                "surfing on a massive green candlestick wave",
                "breaking through a giant wall of resistance",
                "standing on top of a golden mountain of coins",
                "punching through the ceiling with explosive power",
                "flying upward with jet boots leaving fire trail",
                "celebrating victory with confetti and fireworks",
                "holding a giant green arrow pointing to the sky",
            ],
            "bearish": [
                "defending against a storm with a glowing shield",
                "analyzing falling red charts with focused eyes",
                "standing firm in a digital thunderstorm",
                "meditating calmly amid market chaos",
                "building a fortress of stacked coins",
                "wearing armor against incoming red arrows",
            ],
            "neutral": [
                "commanding multiple holographic trading screens",
                "standing at a crossroads of green and red paths",
                "balancing on a scale between bull and bear",
                "studying ancient crypto scrolls",
                "operating a futuristic trading command center",
                "floating in digital meditation pose",
            ]
        }

        # ═══════════════════════════════════════════════════════════════
        # 확장된 배경 풀
        # ═══════════════════════════════════════════════════════════════
        backgrounds = {
            "bullish": [
                "space with giant moon and Earth below, stars everywhere",
                "golden city skyline with fireworks exploding",
                "mountain peak above the clouds at sunrise",
                "stadium filled with cheering crowd and confetti",
                "volcano erupting with golden lava",
                "rainbow bridge leading to golden gates",
            ],
            "bearish": [
                "dark stormy sky with lightning",
                "underwater deep sea with bioluminescent creatures",
                "foggy battlefield with red warning lights",
                "abandoned futuristic city at night",
                "ice cave with cool blue crystals",
            ],
            "neutral": [
                "cyberpunk neon city at night with rain",
                "futuristic trading floor with floating screens",
                "matrix-style digital rain environment",
                "zen garden with holographic trees",
                "space station orbiting Earth",
                "abstract geometric dimension with portals",
            ]
        }

        # ═══════════════════════════════════════════════════════════════
        # 확장된 스타일 풀
        # ═══════════════════════════════════════════════════════════════
        styles = [
            "cinematic 3D render, Pixar quality",
            "cyberpunk neon art, high contrast",
            "anime style, vibrant colors",
            "comic book art, bold outlines",
            "retro 80s synthwave aesthetic",
            "vaporwave art, pink and blue",
            "pixel art, 16-bit gaming style",
            "oil painting, dramatic brushstrokes",
            "watercolor digital art, soft edges",
            "graffiti street art style",
            "low-poly 3D geometric art",
            "holographic iridescent style",
        ]

        # ═══════════════════════════════════════════════════════════════
        # 색상 팔레트 풀
        # ═══════════════════════════════════════════════════════════════
        colors = {
            "bullish": [
                "golden glow and vibrant green neon",
                "orange fire and yellow explosion",
                "pink and gold luxury aesthetic",
                "emerald green and diamond sparkle",
            ],
            "bearish": [
                "cool blue and purple tones",
                "dark red and black dramatic",
                "silver and ice blue",
                "deep ocean blue and teal",
            ],
            "neutral": [
                "blue and purple neon balance",
                "silver and cyan tech look",
                "white and rainbow gradient",
                "monochrome with accent colors",
            ]
        }

        # 랜덤 조합 생성
        selected_character = random.choice(characters)
        selected_action = random.choice(actions.get(mood, actions["neutral"]))
        selected_background = random.choice(backgrounds.get(mood, backgrounds["neutral"]))
        selected_style = random.choice(styles)
        selected_color = random.choice(colors.get(mood, colors["neutral"]))

        # 프롬프트 생성
        prompt = f"{selected_character} {selected_action}, {selected_background}, {selected_color}, {selected_style}, dramatic lighting, 4K quality. No text, no words, no letters, no watermarks, no human faces."

        logger.info(f"🎨 밈 이미지 생성: {selected_character[:30]}... + {selected_action[:20]}...")

        return self.generate_image(
            prompt=prompt.strip(),
            filename=f"crypto_meme_{mood}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            style="crypto-meme"
        )


def test_gemini_image():
    """동기 테스트 함수"""
    try:
        generator = GeminiImageGenerator()

        # 암호화폐 썸네일 생성
        image_path = generator.generate_crypto_thumbnail(
            topic="Bitcoin December 2025 market analysis",
            mood="neutral"
        )

        if image_path:
            print(f"SUCCESS: {image_path}")
            return image_path
        else:
            print("ERROR: 이미지 생성 실패")
            return None

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_gemini_image()
