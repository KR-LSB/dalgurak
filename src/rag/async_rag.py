from asyncio import Semaphore
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
import time
import logging

class AsyncRequestHandler:
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.rate_limit = 10
        self._last_request_time = time.time()
        self.session = None
        self.logger = logging.getLogger('AsyncRequestHandler')
        self.loop = asyncio.get_running_loop()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._request_times = []

    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        async with self.semaphore:
            # Rate limiting with minimum delay
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
                self.logger.error(f"Request processing error: {str(e)}")
                return {"error": str(e)}
            
    async def setup(self):
        """비동기 초기화"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def cleanup(self):
        """리소스 정리"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _check_cache(self, question: str) -> Optional[Dict[str, Any]]:
        """캐시 확인"""
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
        """실제 요청 처리"""
        if not self.rag_system:
            raise ValueError("RAG system not initialized")

        question = request.get('question', '')
        if not question:
            raise ValueError("Question cannot be empty")

        try:
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
                "quality_metrics": self.rag_system._calculate_quality_metrics(response['answer']),
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            raise

    async def process_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """배치 요청 처리"""
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

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        return None