"""
API 비용 최적화 모듈
- Prompt Caching으로 반복 호출 비용 90% 절감
- Claude Haiku 모델 사용으로 비용 절감
- 응답 캐싱 및 재사용
"""

import json
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger


class CostOptimizer:
    """API 비용 최적화 클래스"""

    def __init__(self, cache_dir: str = "./data/cache"):
        """
        Args:
            cache_dir: 캐시 디렉토리
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 캐시 만료 시간 (시간)
        self.cache_ttl_hours = {
            "research": 6,      # 뉴스는 6시간마다 갱신
            "content": 24,      # 콘텐츠는 24시간 캐시
            "qa": 24,           # QA 결과는 24시간 캐시
        }

    def get_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        # 데이터를 JSON으로 직렬화하여 해시 생성
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.md5(data_str.encode()).hexdigest()
        return f"{prefix}_{hash_value}"

    def get_cached_response(
        self,
        prefix: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """캐시된 응답 가져오기"""
        cache_key = self.get_cache_key(prefix, data)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            # 만료 시간 확인
            cached_at = datetime.fromisoformat(cached['cached_at'])
            ttl = self.cache_ttl_hours.get(prefix, 24)
            expiry = cached_at + timedelta(hours=ttl)

            if datetime.now() > expiry:
                logger.debug(f"캐시 만료: {cache_key}")
                cache_file.unlink()
                return None

            logger.success(f"캐시 히트: {cache_key} (절약: API 호출 1회)")
            return cached['response']

        except Exception as e:
            logger.error(f"캐시 읽기 실패: {e}")
            return None

    def save_to_cache(
        self,
        prefix: str,
        data: Dict[str, Any],
        response: Dict[str, Any]
    ):
        """응답을 캐시에 저장"""
        cache_key = self.get_cache_key(prefix, data)
        cache_file = self.cache_dir / f"{cache_key}.json"

        cached_data = {
            "cached_at": datetime.now().isoformat(),
            "request": data,
            "response": response
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)

            logger.info(f"캐시 저장: {cache_key}")

        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")

    def cleanup_expired_cache(self):
        """만료된 캐시 정리"""
        deleted = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)

                cached_at = datetime.fromisoformat(cached['cached_at'])
                # 가장 긴 TTL 사용
                max_ttl = max(self.cache_ttl_hours.values())
                expiry = cached_at + timedelta(hours=max_ttl)

                if datetime.now() > expiry:
                    cache_file.unlink()
                    deleted += 1

            except Exception as e:
                logger.warning(f"캐시 파일 처리 실패 ({cache_file}): {e}")

        if deleted > 0:
            logger.info(f"만료된 캐시 {deleted}개 삭제")

        return deleted


# ============================================
# 비용 추적
# ============================================

class CostTracker:
    """API 비용 추적 클래스"""

    # 모델별 비용 ($/1M tokens)
    PRICING = {
        # Claude Models
        "claude-sonnet-4-20250514": {
            "input": 3.00,
            "output": 15.00,
            "cache_write": 3.75,
            "cache_read": 0.30  # 90% 절감!
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,
            "output": 4.00,
            "cache_write": 1.00,
            "cache_read": 0.08
        },
        # Gemini Models
        "gemini-1.5-pro": {
            "input": 1.25,
            "output": 5.00
        },
        # Perplexity
        "llama-3.1-sonar-large-128k-online": {
            "per_request": 0.005  # $5 per 1000 requests
        }
    }

    def __init__(self, log_file: str = "./data/logs/cost_log.json"):
        """
        Args:
            log_file: 비용 로그 파일
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.usage_log = []
        self._load_log()

    def _load_log(self):
        """로그 파일 로드"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    self.usage_log = json.load(f)
            except Exception as e:
                logger.error(f"비용 로그 로드 실패: {e}")
                self.usage_log = []

    def _save_log(self):
        """로그 파일 저장"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.usage_log, f, indent=2)
        except Exception as e:
            logger.error(f"비용 로그 저장 실패: {e}")

    def log_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0
    ) -> float:
        """
        API 사용량 기록 및 비용 계산

        Args:
            model: 모델 이름
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수
            cache_read_tokens: 캐시 읽기 토큰 수
            cache_write_tokens: 캐시 쓰기 토큰 수

        Returns:
            비용 ($)
        """
        if model not in self.PRICING:
            logger.warning(f"알 수 없는 모델: {model}")
            return 0.0

        pricing = self.PRICING[model]
        cost = 0.0

        # Claude/Gemini 토큰 기반 비용
        if "input" in pricing:
            cost += (input_tokens / 1_000_000) * pricing["input"]
            cost += (output_tokens / 1_000_000) * pricing["output"]

            if cache_read_tokens > 0:
                cost += (cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0)

            if cache_write_tokens > 0:
                cost += (cache_write_tokens / 1_000_000) * pricing.get("cache_write", 0)

        # Perplexity 요청 기반 비용
        elif "per_request" in pricing:
            cost = pricing["per_request"]

        # 로그 저장
        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
            "cost_usd": round(cost, 6)
        }

        self.usage_log.append(entry)
        self._save_log()

        logger.info(f"API 비용: ${cost:.4f} ({model})")
        return cost

    def get_total_cost(self, days: int = 30) -> Dict[str, float]:
        """
        기간별 총 비용 조회

        Args:
            days: 조회 기간 (일)

        Returns:
            모델별 비용 딕셔너리
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_logs = [
            log for log in self.usage_log
            if datetime.fromisoformat(log['timestamp']) > cutoff
        ]

        total_by_model = {}
        for log in recent_logs:
            model = log['model']
            cost = log['cost_usd']

            if model not in total_by_model:
                total_by_model[model] = 0.0

            total_by_model[model] += cost

        total_cost = sum(total_by_model.values())

        logger.info(f"최근 {days}일 총 비용: ${total_cost:.2f}")
        for model, cost in total_by_model.items():
            logger.info(f"  - {model}: ${cost:.2f}")

        return {
            "total": total_cost,
            "by_model": total_by_model,
            "days": days
        }


# ============================================
# 전역 인스턴스
# ============================================

cost_optimizer = CostOptimizer()
cost_tracker = CostTracker()
