"""
설정 관리 모듈

애플리케이션 전역 설정을 관리합니다.

Features:
    - 환경 변수 기반 설정 로드
    - 데이터 클래스 기반 타입 안전성
    - 싱글톤 패턴으로 전역 접근
    - 설정 검증 및 기본값

Example:
    >>> from ai.utils import get_config
    >>> 
    >>> config = get_config()
    >>> print(config.model.name)  # "gpt-3.5-turbo-16k"
    >>> print(config.cache.ttl)   # 7200
    >>> 
    >>> # 커스텀 설정
    >>> custom_config = Config(
    ...     model=ModelConfig(name="gpt-4"),
    ...     cache=CacheConfig(maxsize=10000)
    ... )
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


# 환경 변수 로드
load_dotenv()


@dataclass
class ModelConfig:
    """
    LLM 모델 설정
    
    Attributes:
        name: 모델명 (기본값: gpt-3.5-turbo-16k)
        temperature: 생성 온도 (기본값: 0.7)
        max_tokens: 최대 토큰 수 (기본값: 4096)
        timeout: 요청 타임아웃 (초, 기본값: 30)
        max_retries: 최대 재시도 횟수 (기본값: 2)
    """
    name: str = "gpt-3.5-turbo-16k"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30
    max_retries: int = 2
    
    @classmethod
    def from_env(cls) -> 'ModelConfig':
        """환경 변수에서 설정 로드"""
        return cls(
            name=os.getenv('MODEL_NAME', 'gpt-3.5-turbo-16k'),
            temperature=float(os.getenv('MODEL_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('MODEL_MAX_TOKENS', '4096')),
            timeout=int(os.getenv('MODEL_TIMEOUT', '30')),
            max_retries=int(os.getenv('MODEL_MAX_RETRIES', '2'))
        )


@dataclass
class CacheConfig:
    """
    캐시 설정
    
    Attributes:
        maxsize: 최대 캐시 항목 수 (기본값: 5000)
        ttl: Time-To-Live (초, 기본값: 7200)
        response_cache_size: 응답 캐시 크기 (기본값: 5000)
        embedding_cache_size: 임베딩 캐시 크기 (기본값: 5000)
    """
    maxsize: int = 5000
    ttl: int = 7200  # 2시간
    response_cache_size: int = 5000
    embedding_cache_size: int = 5000
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """환경 변수에서 설정 로드"""
        return cls(
            maxsize=int(os.getenv('CACHE_MAXSIZE', '5000')),
            ttl=int(os.getenv('CACHE_TTL', '7200')),
            response_cache_size=int(os.getenv('RESPONSE_CACHE_SIZE', '5000')),
            embedding_cache_size=int(os.getenv('EMBEDDING_CACHE_SIZE', '5000'))
        )


@dataclass
class RAGConfig:
    """
    RAG 시스템 설정
    
    Attributes:
        persist_directory: 벡터 DB 저장 경로
        chunk_size: 텍스트 청크 크기
        chunk_overlap: 청크 간 중첩 크기
        search_k: 검색 결과 수
        max_concurrent: 최대 동시 요청 수
    """
    persist_directory: str = "recipe_db"
    chunk_size: int = 500
    chunk_overlap: int = 50
    search_k: int = 3
    max_concurrent: int = 5
    max_context_length: int = 1500
    
    @classmethod
    def from_env(cls) -> 'RAGConfig':
        """환경 변수에서 설정 로드"""
        return cls(
            persist_directory=os.getenv('PERSIST_DIRECTORY', 'recipe_db'),
            chunk_size=int(os.getenv('CHUNK_SIZE', '500')),
            chunk_overlap=int(os.getenv('CHUNK_OVERLAP', '50')),
            search_k=int(os.getenv('SEARCH_K', '3')),
            max_concurrent=int(os.getenv('MAX_CONCURRENT', '5')),
            max_context_length=int(os.getenv('MAX_CONTEXT_LENGTH', '1500'))
        )


@dataclass
class CrawlingConfig:
    """
    크롤링 설정
    
    Attributes:
        request_delay: 요청 간 딜레이 (초)
        max_retries: 최대 재시도 횟수
        timeout: 요청 타임아웃 (초)
        batch_size: 배치 크기
        user_agent: User-Agent 문자열
    """
    request_delay: float = 3.0
    max_retries: int = 3
    timeout: int = 30
    batch_size: int = 100
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    @classmethod
    def from_env(cls) -> 'CrawlingConfig':
        """환경 변수에서 설정 로드"""
        return cls(
            request_delay=float(os.getenv('CRAWL_DELAY', '3.0')),
            max_retries=int(os.getenv('CRAWL_MAX_RETRIES', '3')),
            timeout=int(os.getenv('CRAWL_TIMEOUT', '30')),
            batch_size=int(os.getenv('CRAWL_BATCH_SIZE', '100'))
        )


@dataclass
class LoggingConfig:
    """
    로깅 설정
    
    Attributes:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        log_file: 로그 파일 경로
        format: 로그 포맷
    """
    level: str = "INFO"
    log_file: str = "recipe_rag.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """환경 변수에서 설정 로드"""
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'recipe_rag.log')
        )


@dataclass
class Config:
    """
    전역 설정 클래스
    
    모든 설정을 통합 관리합니다.
    
    Attributes:
        model: LLM 모델 설정
        cache: 캐시 설정
        rag: RAG 시스템 설정
        crawling: 크롤링 설정
        logging: 로깅 설정
        
    Example:
        >>> config = Config.from_env()
        >>> print(config.model.name)
        >>> print(config.cache.ttl)
    """
    model: ModelConfig = field(default_factory=ModelConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    crawling: CrawlingConfig = field(default_factory=CrawlingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # API 키 (민감 정보)
    openai_api_key: Optional[str] = field(default=None, repr=False)
    
    def __post_init__(self):
        """초기화 후처리"""
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        환경 변수에서 전체 설정 로드
        
        Returns:
            Config 인스턴스
        """
        return cls(
            model=ModelConfig.from_env(),
            cache=CacheConfig.from_env(),
            rag=RAGConfig.from_env(),
            crawling=CrawlingConfig.from_env(),
            logging=LoggingConfig.from_env(),
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
    
    def validate(self) -> List[str]:
        """
        설정 유효성 검사
        
        Returns:
            오류 메시지 목록 (비어있으면 유효)
        """
        errors = []
        
        # API 키 검증
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        # 모델 설정 검증
        if self.model.temperature < 0 or self.model.temperature > 2:
            errors.append("temperature는 0~2 사이여야 합니다.")
        
        if self.model.max_tokens < 1:
            errors.append("max_tokens는 1 이상이어야 합니다.")
        
        # 캐시 설정 검증
        if self.cache.ttl < 0:
            errors.append("cache.ttl은 0 이상이어야 합니다.")
        
        if self.cache.maxsize < 1:
            errors.append("cache.maxsize는 1 이상이어야 합니다.")
        
        # RAG 설정 검증
        if self.rag.chunk_overlap >= self.rag.chunk_size:
            errors.append("chunk_overlap은 chunk_size보다 작아야 합니다.")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        딕셔너리로 변환 (API 키 제외)
        
        Returns:
            설정 딕셔너리
        """
        return {
            "model": {
                "name": self.model.name,
                "temperature": self.model.temperature,
                "max_tokens": self.model.max_tokens,
                "timeout": self.model.timeout,
                "max_retries": self.model.max_retries
            },
            "cache": {
                "maxsize": self.cache.maxsize,
                "ttl": self.cache.ttl,
                "response_cache_size": self.cache.response_cache_size,
                "embedding_cache_size": self.cache.embedding_cache_size
            },
            "rag": {
                "persist_directory": self.rag.persist_directory,
                "chunk_size": self.rag.chunk_size,
                "chunk_overlap": self.rag.chunk_overlap,
                "search_k": self.rag.search_k,
                "max_concurrent": self.rag.max_concurrent
            },
            "crawling": {
                "request_delay": self.crawling.request_delay,
                "max_retries": self.crawling.max_retries,
                "timeout": self.crawling.timeout,
                "batch_size": self.crawling.batch_size
            },
            "logging": {
                "level": self.logging.level,
                "log_file": self.logging.log_file
            }
        }


# 싱글톤 인스턴스
_config_instance: Optional[Config] = None


def get_config(reload: bool = False) -> Config:
    """
    전역 설정 인스턴스 반환 (싱글톤)
    
    Args:
        reload: True면 설정 다시 로드
        
    Returns:
        Config 인스턴스
        
    Example:
        >>> config = get_config()
        >>> print(config.model.name)
    """
    global _config_instance
    
    if _config_instance is None or reload:
        _config_instance = Config.from_env()
    
    return _config_instance


def create_env_template(filepath: str = ".env.example") -> None:
    """
    환경 변수 템플릿 파일 생성
    
    Args:
        filepath: 생성할 파일 경로
    """
    template = """# Dalgurak AI Configuration
# Copy this file to .env and fill in the values

# === Required ===
OPENAI_API_KEY=your-api-key-here

# === Model Settings ===
MODEL_NAME=gpt-3.5-turbo-16k
MODEL_TEMPERATURE=0.7
MODEL_MAX_TOKENS=4096
MODEL_TIMEOUT=30
MODEL_MAX_RETRIES=2

# === Cache Settings ===
CACHE_MAXSIZE=5000
CACHE_TTL=7200
RESPONSE_CACHE_SIZE=5000
EMBEDDING_CACHE_SIZE=5000

# === RAG Settings ===
PERSIST_DIRECTORY=recipe_db
CHUNK_SIZE=500
CHUNK_OVERLAP=50
SEARCH_K=3
MAX_CONCURRENT=5
MAX_CONTEXT_LENGTH=1500

# === Crawling Settings ===
CRAWL_DELAY=3.0
CRAWL_MAX_RETRIES=3
CRAWL_TIMEOUT=30
CRAWL_BATCH_SIZE=100

# === Logging Settings ===
LOG_LEVEL=INFO
LOG_FILE=recipe_rag.log
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"환경 변수 템플릿 생성 완료: {filepath}")