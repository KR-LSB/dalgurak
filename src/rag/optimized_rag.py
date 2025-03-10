import traceback
from typing import Dict, List, Any, Optional
import asyncio
from collections import defaultdict
import gc
from pathlib import Path
import pickle
import re
import concurrent.futures
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from functools import lru_cache
from cachetools import TTLCache
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
import time
import hashlib
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import warnings
from .async_rag import AsyncRequestHandler

warnings.filterwarnings("ignore", category=DeprecationWarning)

class OptimizedCache:
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self._cache = {}       # 항상 _cache 사용
        self.maxsize = maxsize
        self.ttl = ttl
        
    def set(self, key: str, value: Any) -> None:
        self._cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        if len(self._cache) > self.maxsize:
            self._cleanup_oldest()
            
    def get(self, key: str, default: Any = None) -> Any:
        if key in self._cache:
            item = self._cache[key]
            if time.time() - item['timestamp'] < self.ttl:
                return item['value']
            del self._cache[key]
        return default

    def __contains__(self, key: str) -> bool:
        if key in self._cache:
            if time.time() - self._cache[key]['timestamp'] < self.ttl:
                return True
            del self._cache[key]
        return False

    def __setitem__(self, key: str, value: Any) -> None:
        self._cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        
        if len(self._cache) > self.maxsize:
            self._cleanup_oldest()

    def __getitem__(self, key: str) -> Any:
        item = self._cache.get(key)
        if item and (time.time() - item['timestamp'] < self.ttl):
            return item['value']
        if key in self._cache:
            del self._cache[key]
        raise KeyError(key)

    def _cleanup_oldest(self) -> None:
        """가장 오래된 항목 제거"""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), 
                        key=lambda k: self._cache[k]['timestamp'])
        del self._cache[oldest_key]

    def clear(self) -> None:
        """캐시 초기화"""
        self._cache.clear()

    def update(self, other_dict):
        """다른 딕셔너리로 캐시 업데이트"""
        if not isinstance(other_dict, dict):
            raise TypeError("Expected dictionary for update")
        for key, value in other_dict.items():
            self.set(key, value)
    
    def items(self):
        """캐시 아이템 순회"""
        return [(k, v['value']) for k, v in self._cache.items() 
                if time.time() - v['timestamp'] < self.ttl]

    def values(self):
        """캐시 값 순회"""
        return [v['value'] for v in self._cache.values() 
                if time.time() - v['timestamp'] < self.ttl]

    def keys(self):
        """캐시 키 순회"""
        return [k for k, v in self._cache.items() 
                if time.time() - v['timestamp'] < self.ttl]

    def __iter__(self):
        """반복자 구현"""
        return iter(self.keys())

    def __len__(self):
        """캐시 크기"""
        return len([k for k, v in self._cache.items() 
                   if time.time() - v['timestamp'] < self.ttl])

class OptimizedRecipeRAG:
    def __init__(self, persist_directory: str = "recipe_db", max_concurrent: int = 5):
        """
        RAG 시스템 초기화
        Args:
            persist_directory (str): 벡터 저장소 디렉토리
            max_concurrent (int): 최대 동시 요청 수
        """
        load_dotenv()
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.persist_directory = persist_directory
        self.logger = self._setup_logger()
        self.embeddings = OpenAIEmbeddings()
        
        # 성능 최적화 설정
        self.chunk_size = 256
        self.chunk_overlap = 20
        self.start_time = time.time()
        
        # 동시성 제어 설정
        self.max_concurrent = max_concurrent
        self.request_handler = AsyncRequestHandler(max_concurrent)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # 캐시 설정
        self.response_cache = OptimizedCache(maxsize=5000, ttl=7200)
        self.embedding_cache = OptimizedCache(maxsize=5000, ttl=7200)
        
        # 임베딩 로드
        self.load_precomputed_embeddings()
        
        # 벡터 DB 초기화
        self.vectordb = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_metadata={"hnsw:space": "cosine"}
        )
        
        # LLM 설정
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo-16k",
            temperature=0.7,
            request_timeout=30,
            max_retries=2
        )
        
        # 메모리 설정
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
            input_key="question"
        )
        
        # QA 체인 설정
        self.qa_chain = self._setup_qa_chain()
        
        # 성능 모니터링 초기화
        self.metrics = defaultdict(list)
        self.error_count = 0
        self.request_count = 0
        self.cache_hits = 0
   

    def _get_cache_key(self, text: str) -> str:
        """캐시 키 생성"""
        return hashlib.md5(text.encode()).hexdigest()


    def _setup_logger(self):
        """로거 설정"""
        logger = logging.getLogger('OptimizedRecipeRAG')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            fh = logging.FileHandler('recipe_rag.log')
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            logger.addHandler(fh)
            logger.addHandler(ch)
        
        return logger

    def _setup_http_client(self):
        """HTTP 클라이언트 설정"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _initialize_monitoring(self):
        """성능 모니터링 초기화"""
        self.metrics = defaultdict(list)
        self.error_count = 0
        self.request_count = 0
        self.cache_hits = 0

    def load_precomputed_embeddings(self):
        """미리 계산된 임베딩 로드"""
        try:
            embeddings_file = Path(self.persist_directory) / "precomputed_embeddings.pkl"
            if embeddings_file.exists():
                with open(embeddings_file, 'rb') as f:
                    loaded_embeddings = pickle.load(f)
                    if isinstance(loaded_embeddings, dict):
                        for key, value in loaded_embeddings.items():
                            self.embedding_cache.set(key, value)
                    self.logger.info(f"Loaded {len(loaded_embeddings)} precomputed embeddings")
            else:
                self._precompute_common_embeddings()
        except Exception as e:
            self.logger.error(f"임베딩 로드 중 오류: {str(e)}")
            self._precompute_common_embeddings()

    def _precompute_common_embeddings(self):
        """자주 사용되는 임베딩 미리 계산"""
        common_queries = [
            "김치찌개", "된장찌개", "비빔밥",
            "조리방법", "요리팁", "초보자",
            "재료준비", "양념장", "기본레시피"
        ]
        
        try:
            for query in common_queries:
                embedding = self.embeddings.embed_query(query)
                self.embedding_cache.set(query, embedding)
            
            # 임베딩 저장
            self._save_embeddings()
            self.logger.info(f"Precomputed {len(common_queries)} common embeddings")
        except Exception as e:
            self.logger.error(f"임베딩 계산 중 오류: {str(e)}")

    def _save_embeddings(self):
        """임베딩 캐시 저장"""
        try:
            embeddings_file = Path(self.persist_directory) / "precomputed_embeddings.pkl"
            embeddings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 캐시를 딕셔너리로 변환
            embeddings_dict = dict(self.embedding_cache.items())
            
            with open(embeddings_file, 'wb') as f:
                pickle.dump(embeddings_dict, f)
            
            self.logger.info(f"Saved {len(embeddings_dict)} embeddings")
        except Exception as e:
            self.logger.error(f"임베딩 저장 중 오류: {str(e)}")
    
    def _setup_qa_chain(self):
        """QA 체인 설정"""
        template = """당신은 한식 전문 요리사입니다. 다음 형식에 맞춰 상세하게 답변해주세요:

질문: {question}

컨텍스트: {context}

답변 형식:
1. 기본 정보
   - 필수 재료
   - 조리 시간
   - 난이도

2. 상세 내용
   - 구체적인 수치와 시간
   - 단계별 명확한 설명
   - 중요 포인트 강조

3. 전문가 팁
   - 실수하기 쉬운 부분 주의사항
   - 맛있게 만드는 비법
   - 활용 아이디어

위 형식을 반드시 지켜 답변해주세요."""

        QA_PROMPT = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self._get_optimized_retriever(),
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT},
            return_source_documents=True,
            verbose=True
        )

    def _get_optimized_retriever(self):
        """최적화된 검색기 설정"""
        return self.vectordb.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": 3
            }
        )

    @lru_cache(maxsize=1000)
    def _compute_embedding(self, text: str) -> List[float]:
        """임베딩 계산 (캐시 적용)"""
        try:
            cache_key = hashlib.md5(text.encode()).hexdigest()
            
            if cache_key in self.embedding_cache:
                self.cache_hits += 1
                return self.embedding_cache[cache_key]
            
            embedding = self.embeddings.embed_query(text)
            self.embedding_cache[cache_key] = embedding
            return embedding
            
        except Exception as e:
            self.logger.error(f"임베딩 계산 중 오류: {str(e)}")
            return None
        
    def _get_context(self, question: str) -> str:
        """컨텍스트 검색"""
        try:
            similar_docs = self.vectordb.similarity_search(
                query=question,
                k=3
            )
            
            context_parts = []
            seen_content = set()
            
            for doc in similar_docs:
                content = doc.page_content.strip()
                if content and content not in seen_content:
                    context_parts.append(content)
                    seen_content.add(content)
            
            context = "\n\n".join(context_parts)
            
            if len(context) > 1500:
                context = context[:1500]
            
            return context
            
        except Exception as e:
            self.logger.error(f"컨텍스트 검색 중 오류: {str(e)}")
            return ""

    async def _get_context_async(self, question: str) -> str:
        """비동기 컨텍스트 검색"""
        try:
            cache_key = f"context_{hashlib.md5(question.encode()).hexdigest()}"
            
            if cache_key in self.response_cache:
                self.cache_hits += 1
                return self.response_cache[cache_key]

            similar_docs = self.vectordb.similarity_search(
                query=question,
                k=3
            )
            
            context_parts = []
            seen_content = set()
            
            for doc in similar_docs:
                content = doc.page_content.strip()
                if content and content not in seen_content:
                    relevance = await self._check_relevance_async(content, question)
                    if relevance >= 0.3:
                        context_parts.append(content)
                        seen_content.add(content)
            
            context = "\n\n".join(context_parts)
            
            if len(context) > 1500:
                context = context[:1500]
            
            if not context and similar_docs:
                context = similar_docs[0].page_content
            
            self.response_cache[cache_key] = context
            return context
            
        except Exception as e:
            self.logger.error(f"비동기 컨텍스트 검색 중 오류: {str(e)}")
            return ""
        
    def _check_relevance(self, content: str, query: str) -> float:
        """최적화된 관련성 검사"""
        try:
            # 캐시 키 생성
            cache_key = f"relevance_{self._get_cache_key(content + query)}"
            cached_score = self.embedding_cache.get(cache_key)
            
            if cached_score is not None:
                return cached_score

            # 텍스트 전처리
            content_words = set(content.lower().split())
            query_words = set(query.lower().split())

            # 빠른 키워드 매칭
            cooking_keywords = {
                '레시피': 1.0, '요리': 1.0, '만들기': 0.8,
                '재료': 0.9, '조리': 0.9, '끓이기': 0.7,
                '볶기': 0.7, '굽기': 0.7, '찌기': 0.7,
                '양념': 0.8, '간': 0.6, '맛': 0.6
            }

            # 키워드 점수 계산
            keyword_score = sum(weight for word, weight in cooking_keywords.items() 
                              if word in content_words)
            max_keyword_score = sum(cooking_keywords.values())
            normalized_keyword_score = keyword_score / max_keyword_score

            # 쿼리 매칭 점수
            common_words = query_words.intersection(content_words)
            query_match_score = len(common_words) / len(query_words) if query_words else 0

            # 최종 점수 계산
            final_score = min((normalized_keyword_score * 0.7) + 
                            (query_match_score * 0.3), 1.0)

            # 결과 캐시
            self.embedding_cache.set(cache_key, final_score)

            return final_score

        except Exception as e:
            self.logger.error(f"관련성 검사 중 오류: {str(e)}")
            return 0.0

    async def _check_relevance_async(self, content: str, query: str) -> float:
        """비동기 관련성 검사"""
        return self._check_relevance(content, query)

    def _calculate_quality_metrics(self, response: str) -> Dict[str, float]:
        """개선된 품질 메트릭 계산"""
        try:
            # 텍스트 정규화
            text = response.lower() if isinstance(response, str) else str(response).lower()
            
            # 1. 완성도 평가 (가중치: 0.4)
            required_sections = {
                '재료': ['재료', '준비물', '필요한', '있어야'],
                '조리': ['조리', '만들기', '요리', '방법', '과정'],
                '팁': ['팁', '주의', '포인트', '중요', '비법']
            }
            
            section_scores = []
            for section, keywords in required_sections.items():
                section_score = any(keyword in text for keyword in keywords)
                section_scores.append(section_score)
            
            completeness = sum(section_scores) / len(required_sections)
            
            # 2. 관련성 평가 (가중치: 0.4)
            relevance_keywords = {
                '고급': 1.0,  # 핵심 요리 용어
                '요리': 1.0,
                '레시피': 1.0,
                '만들기': 0.9,
                '조리법': 0.9,
                '끓이기': 0.8,
                '볶기': 0.8,
                '굽기': 0.8,
                '재료': 0.8,
                '양념': 0.8,
                '간': 0.7,
                '맛': 0.7,
                '음식': 0.7,
                '식재료': 0.7,
                '준비': 0.6,
                '방법': 0.6,
                '순서': 0.6,
                '시간': 0.5,
                '정도': 0.5,
                '팁': 0.5
            }
            
            matched_keywords = [(keyword, weight) for keyword, weight in relevance_keywords.items() 
                              if keyword in text]
            
            if matched_keywords:
                relevance = sum(weight for _, weight in matched_keywords) / len(matched_keywords)
            else:
                relevance = 0.0
            
            # 3. 구조화 평가 (가중치: 0.2)
            structure_points = 0
            
            # 번호 매기기 확인
            if re.search(r'\d+\.|\d+\)', text):
                structure_points += 0.4
            
            # 구분자 사용 확인
            if re.search(r'[-•*]', text):
                structure_points += 0.3
            
            # 단락 구분 확인
            paragraphs = text.split('\n\n')
            if len(paragraphs) >= 3:
                structure_points += 0.3
            
            # 섹션 헤더 확인
            if re.search(r'(기본 정보|재료 준비|조리 순서|요리 팁):', text):
                structure_points += 0.4
            
            # 최종 점수 계산 (가중치 적용)
            final_metrics = {
                'completeness': round(completeness, 2),
                'relevance': round(min(relevance * 1.2, 1.0), 2),  # 관련성 점수 약간 상향 조정
                'structure': round(min(structure_points, 1.0), 2)
            }
            
            return final_metrics
            
        except Exception as e:
            self.logger.error(f"품질 메트릭 계산 중 오류: {str(e)}")
            return {
                'completeness': 0.0,
                'relevance': 0.0,
                'structure': 0.0
            }

    def _record_metrics(self, start_time: float, metrics: Dict[str, float]):
        """성능 메트릭 기록"""
        execution_time = time.time() - start_time
        self.metrics['execution_time'].append(execution_time)
        self.metrics['quality_scores'].append(metrics)
        
        # 평균 계산
        avg_exec_time = sum(self.metrics['execution_time']) / len(self.metrics['execution_time'])
        cache_hit_rate = self.cache_hits / self.request_count if self.request_count > 0 else 0
        
        self.logger.info(f"""
        성능 메트릭:
        - 실행 시간: {execution_time:.2f}초 (평균: {avg_exec_time:.2f}초)
        - 캐시 적중률: {cache_hit_rate:.2%}
        - 품질 점수: {metrics}
        """)

    def ask(self, question: str) -> Dict[str, Any]:
        """질문 처리 (오류 추적 강화)"""
        start_time = time.time()
        self.request_count += 1

        try:
            # 캐시 확인
            cache_key = self._get_cache_key(question)
            cached_response = self.response_cache.get(cache_key)
            
            if cached_response:
                self.cache_hits += 1
                self.logger.info(f"Cache hit for query: {question}")
                return {
                    "answer": cached_response,
                    "execution_time": time.time() - start_time,
                    "quality_metrics": self._calculate_quality_metrics(cached_response),
                    "source": "cache"
                }

            # 컨텍스트 검색
            try:
                context = self._get_context(question)
                if not context:
                    self.logger.warning(f"No context found for query: {question}")
            except Exception as e:
                self.logger.error(f"Context retrieval error: {str(e)}")
                context = ""

            # 응답 생성
            try:
                self.logger.info(f"Generating response for query: {question}")
                response = self.qa_chain.invoke({
                    "question": question,
                    "context": context
                })
                self.logger.info("Response generated successfully")
            except Exception as e:
                self.logger.error(f"Response generation error: {str(e)}")
                raise

            answer = response.get('answer', '')
            if not answer:
                raise ValueError("Empty response from QA chain")

            # 품질 메트릭 계산
            quality_metrics = self._calculate_quality_metrics(answer)

            result = {
                "answer": answer,
                "execution_time": time.time() - start_time,
                "quality_metrics": quality_metrics,
                "context_length": len(context)
            }

            # 품질이 좋은 응답만 캐시
            if quality_metrics['completeness'] >= 0.5 and quality_metrics['relevance'] >= 0.5:
                self.response_cache.set(cache_key, answer)
                self.logger.info("Response cached")

            return result

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error in ask method: {str(e)}")
            self.logger.error(f"Detailed traceback: {traceback.format_exc()}")
            return {
                "answer": f"죄송합니다. 오류가 발생했습니다: {str(e)}",
                "execution_time": time.time() - start_time,
                "quality_metrics": {
                    'completeness': 0.0,
                    'relevance': 0.0,
                    'structure': 0.0
                },
                "error": str(e)
            }

    async def ask_async(self, question: str) -> Dict[str, Any]:
        """단일 질문 비동기 처리"""
        # 빈 질문 체크
        if not question.strip():
            return {
                "answer": "질문을 입력해주세요.",
                "execution_time": 0.0,
                "source": "empty",
                "quality_metrics": {
                    "completeness": 0.0,
                    "relevance": 0.0,
                    "structure": 0.0
                }
            }
        
        # 지역 변수 tasks 초기화
        context_task = None
        embedding_task = None
        
        self.request_count += 1
        start_time = time.time()
        
        try:
            # 캐시 확인
            cache_key = hashlib.md5(question.encode()).hexdigest()
            if cache_key in self.response_cache:
                self.cache_hits += 1
                cached_response = self.response_cache[cache_key].copy()
                cached_response['execution_time'] = 0.1
                cached_response['source'] = 'cache'
                return cached_response
            
            # 현재 스레드의 이벤트 루프 확인
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 이벤트 루프가 없는 경우 새로 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            # 비동기 함수 직접 호출 (create_task 사용하지 않음)
            context = await self._get_context_async(question)
            embeddings = await self._compute_embedding_async(question)
            
            # 응답 생성
            response = await self.qa_chain.ainvoke({
                "question": question,
                "context": context
            })
            
            # 품질 메트릭 계산
            quality_metrics = self._calculate_quality_metrics(response['answer'])
            
            # 결과 생성
            result = {
                "answer": response['answer'],
                "execution_time": time.time() - start_time,
                "quality_metrics": quality_metrics,
                "source": "direct",
                "source_documents": response.get('source_documents', [])
            }
            
            # 캐시 저장 (품질 점수 관계없이 저장)
            self.response_cache[cache_key] = result.copy()
            
            # 메트릭 기록
            self._record_metrics(start_time, quality_metrics)
            
            return result
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"비동기 질문 처리 중 오류 발생: {str(e)}")
            return {
                "answer": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                "execution_time": time.time() - start_time,
                "source": "error",
                "quality_metrics": {
                    "completeness": 0.0,
                    "relevance": 0.0,
                    "structure": 0.0
                },
                "error": str(e)
            }

    async def process_batch(self, questions: List[str]) -> List[Dict[str, Any]]:
        """여러 질문 배치 처리"""
        async with self.request_handler.session:
            tasks = [self.ask_async(q) for q in questions]
            return await asyncio.gather(*tasks, return_exceptions=True)

    def _get_cached_response(self, cache_key: str) -> Dict[str, Any]:
        """캐시된 응답 반환"""
        cached_response = self.response_cache[cache_key].copy()
        cached_response['execution_time'] = 0.1
        cached_response['source'] = 'cache'
        return cached_response

    async def _process_response(self, 
                              response: Dict, 
                              start_time: float, 
                              cache_key: str) -> Dict[str, Any]:
        """응답 처리 및 캐시 저장"""
        quality_metrics = self._calculate_quality_metrics(response['answer'])

        result = {
            "answer": response['answer'],
            "execution_time": time.time() - start_time,
            "quality_metrics": quality_metrics,
            "source_documents": response.get('source_documents', [])
        }

        if quality_metrics['relevance'] >= 0.5:
            self.response_cache[cache_key] = result.copy()

        self._record_metrics(start_time, quality_metrics)
        return result

    def _handle_error(self, error: Exception, start_time: float) -> Dict[str, Any]:
        """에러 처리"""
        self.error_count += 1
        self.logger.error(f"비동기 질문 처리 중 오류 발생: {str(error)}")
        return {
            "answer": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
            "execution_time": time.time() - start_time,
            "quality_metrics": {
                "completeness": 0.0,
                "relevance": 0.0,
                "structure": 0.0
            },
            "error": str(error)
        }
        
    async def _compute_embedding_async(self, text: str) -> List[float]:
        """비동기 임베딩 계산"""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        
        if cache_key in self.embedding_cache:
            self.cache_hits += 1
            return self.embedding_cache[cache_key]
        
        embedding = await asyncio.to_thread(self.embeddings.embed_query, text)
        self.embedding_cache[cache_key] = embedding
        return embedding

    async def setup(self):
        """비동기 초기화"""
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        await self.request_handler.setup()

    async def cleanup(self):
        """리소스 정리"""
        await self.request_handler.cleanup()

    def _get_optimized_context(self, question: str) -> str:
        """최적화된 컨텍스트 검색"""
        try:
            # 검색어 최적화
            search_terms = self._extract_search_terms(question)
            
            similar_docs = self.vectordb.similarity_search(
                query=' '.join(search_terms),
                k=3
            )
            
            context_parts = []
            seen_content = set()
            total_length = 0
            max_length = 1500
            
            for doc in similar_docs:
                content = doc.page_content.strip()
                if content and content not in seen_content:
                    if total_length + len(content) > max_length:
                        # 길이 제한에 도달하면 중요 부분만 추출
                        content = self._extract_key_parts(content, max_length - total_length)
                    
                    context_parts.append(content)
                    seen_content.add(content)
                    total_length += len(content)
                    
                    if total_length >= max_length:
                        break
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"컨텍스트 검색 중 오류: {str(e)}")
            return ""

    def _extract_search_terms(self, question: str) -> List[str]:
        """검색어 최적화"""
        # 기본 전처리
        text = question.lower()
        
        # 불용어 제거
        stop_words = {'좀', '주세요', '알려주세요', '있나요', '싶은데', '방법', '어떻게'}
        words = [word for word in text.split() if word not in stop_words]
        
        # 요리 관련 키워드 가중치 부여
        cooking_terms = {'레시피', '요리', '만드는', '조리', '끓이는', '만드는'}
        weighted_terms = []
        
        for word in words:
            if word in cooking_terms:
                weighted_terms.extend([word] * 2)  # 중요 단어 가중치
            else:
                weighted_terms.append(word)
        
        return weighted_terms

    def _extract_key_parts(self, text: str, max_length: int) -> str:
        """중요 부분 추출"""
        # 문장 단위로 분리
        sentences = text.split('.')
        
        # 중요도 점수 계산
        scored_sentences = []
        important_words = {'재료', '조리', '방법', '순서', '팁', '주의', '중요'}
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 중요 단어 포함 여부로 점수 계산
            score = sum(1 for word in important_words if word in sentence.lower())
            scored_sentences.append((sentence, score))
        
        # 점수 기준 정렬
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # 길이 제한 내에서 중요 문장 선택
        result = []
        current_length = 0
        
        for sentence, _ in scored_sentences:
            if current_length + len(sentence) > max_length:
                break
            result.append(sentence)
            current_length += len(sentence) + 1  # +1 for period
        
        return '. '.join(result)

    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        try:
            stats = {
                "total_requests": self.request_count,
                "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
                "cache_hit_rate": self.cache_hits / self.request_count if self.request_count > 0 else 0,
                "avg_execution_time": sum(self.metrics['execution_time']) / len(self.metrics['execution_time'])
                if self.metrics['execution_time'] else 0,
                "quality_metrics": {
                    "avg_completeness": sum(m['completeness'] for m in self.metrics['quality_scores']) / len(self.metrics['quality_scores'])
                    if self.metrics['quality_scores'] else 0,
                    "avg_relevance": sum(m['relevance'] for m in self.metrics['quality_scores']) / len(self.metrics['quality_scores'])
                    if self.metrics['quality_scores'] else 0,
                    "avg_structure": sum(m['structure'] for m in self.metrics['quality_scores']) / len(self.metrics['quality_scores'])
                    if self.metrics['quality_scores'] else 0
                }
            }
            return stats
        except Exception as e:
            self.logger.error(f"성능 통계 계산 중 오류 발생: {str(e)}")
            return {}

async def cleanup(self):
    """리소스 정리"""
    try:
        # 캐시 정리
        self.response_cache.clear()
        self.embedding_cache.clear()
        
        # 메모리 정리
        if hasattr(self, 'memory'):
            self.memory.clear()
        
        # 벡터 DB 연결 해제
        if hasattr(self, 'vectordb'):
            self.vectordb = None
            
        # 세션 닫기
        if hasattr(self, 'request_handler') and hasattr(self.request_handler, 'session'):
            if self.request_handler.session:
                try:
                    await self.request_handler.session.close()
                except:
                    pass
            self.request_handler.session = None
            
        # 가비지 컬렉션 실행
        gc.collect()
        
        self.logger.info("리소스 정리 완료")
    except Exception as e:
        self.logger.error(f"리소스 정리 중 오류 발생: {str(e)}")

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.cleanup()
        if exc_type is not None:
            self.logger.error(f"컨텍스트 매니저 종료 중 오류 발생: {str(exc_val)}")
            return False
        return True