"""
비동기 요청 처리 핸들러

세마포어 기반 동시성 제어 및 Rate Limiting 구현으로
API 안정성을 확보하면서 높은 처리량을 유지합니다.

Features:
    - 세마포어 기반 동시성 제어 (기본 5개)
    - Rate Limiting (기본 10 req/s)
    - 배치 요청 처리
    - 자동 재시도 및 에러 처리

Example:
    >>> async with AsyncRequestHandler(max_concurrent=5) as handler:
    ...     results = await handler.process_batch(requests)
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import aiohttp


logger = logging.getLogger(__name__)


class AsyncRequestHandler:
    """
    비동기 요청 처리 핸들러
    
    RAG 시스템의 비동기 질의 처리를 담당합니다.
    세마포어로 동시 요청 수를 제한하고, Rate Limiting으로
    API 호출 빈도를 조절합니다.
    
    Args:
        max_concurrent: 최대 동시 요청 수 (기본값: 5)
        rate_limit: 초당 최대 요청 수 (기본값: 10)
    
    Attributes:
        semaphore: 동시성 제어용 세마포어
        session: aiohttp 클라이언트 세션
        rag_system: 연결된 RAG 시스템 참조
    """
    
    def __init__(self, max_concurrent: int = 5, rate_limit: int = 10):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self._last_request_time = time.time()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._request_times: List[float] = []
        self.rag_system = None  # RAG 시스템 참조 (외부에서 설정)

    async def setup(self) -> None:
        """
        비동기 세션 초기화
        
        aiohttp ClientSession을 생성합니다.
        Context Manager 진입 시 자동 호출됩니다.
        """
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def cleanup(self) -> None:
        """
        리소스 정리
        
        aiohttp 세션을 종료합니다.
        Context Manager 종료 시 자동 호출됩니다.
        """
        if self.session:
            await self.session.close()
            self.session = None

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 요청 처리 (Rate Limiting 적용)
        
        세마포어로 동시 실행을 제한하고,
        Rate Limiting으로 요청 간격을 조절합니다.
        
        Args:
            request: 요청 데이터 (question 키 필수)
            
        Returns:
            처리 결과 딕셔너리:
            - question: 원본 질문
            - answer: 응답
            - quality_metrics: 품질 메트릭
            - timestamp: 처리 시간
        """
        async with self.semaphore:
            # Rate Limiting
            current_time = time.time()
            min_delay = 1.0 / self.rate_limit
            time_since_last = current_time - self._last_request_time

            if time_since_last < min_delay:
                await asyncio.sleep(min_delay - time_since_last)

            try:
                result = await self._handle_request(request)
                self._last_request_time = time.time()
                self._request_times.append(self._last_request_time)
                return result
            except Exception as e:
                logger.error(f"Request processing error: {str(e)}")
                return {"error": str(e), "status": "error"}

    async def _check_cache(self, question: str) -> Optional[Dict[str, Any]]:
        """
        캐시 확인
        
        RAG 시스템의 응답 캐시에서 이전 응답을 조회합니다.
        
        Args:
            question: 질문 문자열
            
        Returns:
            캐시된 응답 또는 None
        """
        if self.rag_system and hasattr(self.rag_system, 'response_cache'):
            cache_key = self.rag_system._get_cache_key(question)
            if cache_key in self.rag_system.response_cache:
                self.rag_system.cache_hits += 1
                return {
                    **self.rag_system.response_cache[cache_key],
                    'source': 'cache',
                    'cached_at': time.time()
                }
        return None

    async def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        실제 요청 처리 로직
        
        Args:
            request: 요청 데이터
            
        Returns:
            처리 결과
            
        Raises:
            ValueError: RAG 시스템 미설정 또는 빈 질문
        """
        if not self.rag_system:
            raise ValueError("RAG system not initialized")

        question = request.get('question', '')
        if not question:
            raise ValueError("Question cannot be empty")

        try:
            # 캐시 확인
            cached = await self._check_cache(question)
            if cached:
                return cached

            # 컨텍스트와 임베딩 동시 처리
            context, embedding = await asyncio.gather(
                self.rag_system._get_context_async(question),
                self.rag_system._compute_embedding_async(question)
            )

            # 응답 생성
            response = await self.rag_system.qa_chain.ainvoke({
                "question": question,
                "context": context
            })

            return {
                "question": question,
                "answer": response['answer'],
                "context_used": bool(context),
                "quality_metrics": self.rag_system._calculate_quality_metrics(
                    response['answer']
                ),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise

    async def process_batch(
        self, 
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        배치 요청 처리
        
        여러 요청을 동시에 처리합니다.
        각 요청은 세마포어와 Rate Limiting이 적용됩니다.
        
        Args:
            requests: 요청 리스트
            
        Returns:
            결과 리스트 (입력 순서 유지)
        """
        try:
            await self.setup()
            tasks = [self.process_request(req) for req in requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append({
                        "error": str(result),
                        "status": "error",
                        "timestamp": time.time()
                    })
                else:
                    processed_results.append(result)
            return processed_results

        finally:
            await self.cleanup()

    def get_stats(self) -> Dict[str, Any]:
        """
        요청 통계 반환
        
        Returns:
            total_requests: 총 처리 요청 수
            max_concurrent: 최대 동시 요청 수
            rate_limit: 초당 요청 제한
            last_request_time: 마지막 요청 시간
        """
        return {
            "total_requests": len(self._request_times),
            "max_concurrent": self.max_concurrent,
            "rate_limit": self.rate_limit,
            "last_request_time": self._last_request_time
        }

    async def __aenter__(self) -> 'AsyncRequestHandler':
        """Context Manager 진입"""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context Manager 종료"""
        await self.cleanup()