# 🤖 Dalgurak AI Module

> 도메인 특화 RAG 시스템으로 **97% 응답 정확도** 달성

## 📌 개요

Dalgurak AI 모듈은 요리 도메인에 특화된 **RAG(Retrieval-Augmented Generation)** 시스템입니다.

7,500개 이상의 한국 레시피 데이터를 기반으로 범용 LLM 대비 **29%p 높은 정확도**를 달성했습니다.

## 🏗️ 모듈 구조

```
ai/
├── core/                    # 핵심 RAG 시스템
│   ├── rag_engine.py        # OptimizedRecipeRAG 메인 엔진
│   ├── async_handler.py     # 비동기 요청 처리
│   └── cache.py             # TTL 기반 캐시 시스템
│
├── data/                    # 데이터 파이프라인
│   ├── collectors.py        # 웹 크롤러 (만개의레시피, 네이버)
│   ├── processor.py         # 데이터 정제/구조화
│   └── embedder.py          # 벡터 임베딩 생성
│
├── features/                # 부가 기능
│   └── substitution.py      # 대체 재료 추천
│
├── evaluation/              # 성능 평가
│   └── metrics.py           # 정확도/품질 측정
│
└── utils/                   # 유틸리티
    └── config.py            # 설정 관리
```

## 🚀 Quick Start

### 1. 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
OPENAI_API_KEY=your_api_key_here
```

### 3. 사용 예시

```python
from ai.core import OptimizedRecipeRAG

# RAG 시스템 초기화
rag = OptimizedRecipeRAG(persist_directory="recipe_db")

# 질문하기
response = rag.ask("김치찌개 맛있게 끓이는 방법")
print(response['answer'])
print(f"응답 시간: {response['execution_time']:.3f}초")

# 성능 통계
stats = rag.get_performance_stats()
print(f"캐시 히트율: {stats['cache_hit_rate']:.1%}")
```

### 4. 비동기 배치 처리

```python
import asyncio

async def batch_query():
    questions = [
        "된장찌개 레시피",
        "불고기 양념 비율",
        "계란찜 만드는 법"
    ]
    results = await rag.process_batch(questions)
    return results

results = asyncio.run(batch_query())
```

## 💡 핵심 기술

### 1. TTL 기반 2단계 캐싱

```python
# 응답 캐시 + 임베딩 캐시
response_cache = OptimizedCache(maxsize=5000, ttl=7200)
embedding_cache = OptimizedCache(maxsize=5000, ttl=7200)
```

- **82% 캐시 히트율** 달성
- 반복 질의 응답 시간 90% 단축

### 2. 도메인 특화 프롬프트

```python
template = """당신은 한식 전문 요리사입니다.

답변 형식:
1. 기본 정보 (재료, 시간, 난이도)
2. 상세 조리법 (단계별 설명)
3. 전문가 팁 (주의사항, 비법)
"""
```

### 3. 품질 메트릭 자동 평가

```python
quality_metrics = {
    'completeness': 0.85,  # 필수 정보 포함도
    'relevance': 0.92,     # 질문-응답 관련성
    'structure': 0.78      # 구조화 점수
}
```

## 📊 성능 지표

| 메트릭 | Dalgurak | ChatGPT | 개선율 |
|:---:|:---:|:---:|:---:|
| 응답 정확도 | **97%** | 68% | +29%p |
| 평균 응답 시간 | **0.08초** | 2.1초 | 96% 감소 |
| 캐시 히트율 | **82%** | N/A | - |
| 레시피 완성도 | **94%** | 71% | +23%p |

## 🔧 API Reference

### OptimizedRecipeRAG

```python
class OptimizedRecipeRAG:
    def __init__(
        self, 
        persist_directory: str = "recipe_db",
        max_concurrent: int = 5
    ):
        """
        Args:
            persist_directory: 벡터 DB 저장 경로
            max_concurrent: 최대 동시 요청 수
        """
    
    def ask(self, question: str) -> Dict[str, Any]:
        """동기 질문 처리"""
    
    async def ask_async(self, question: str) -> Dict[str, Any]:
        """비동기 질문 처리"""
    
    async def process_batch(self, questions: List[str]) -> List[Dict]:
        """배치 처리"""
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
```

### 응답 형식

```python
{
    "answer": "김치찌개 레시피...",
    "execution_time": 0.082,
    "quality_metrics": {
        "completeness": 0.85,
        "relevance": 0.92,
        "structure": 0.78
    },
    "source": "direct"  # or "cache"
}
```

## 📁 데이터 파이프라인

```bash
# 1. 데이터 수집
python -m ai.data.collectors

# 2. 데이터 처리
python -m ai.data.processor

# 3. 임베딩 생성
python -m ai.data.embedder --input data/processed/recipes.json
```

## 🧪 테스트

```python
from ai.evaluation import RAGEvaluator, run_evaluation

# 평가 실행
summary = run_evaluation(rag_system)
print(f"평균 정확도: {summary['avg_accuracy']:.2%}")
```

## 📝 License

MIT License
