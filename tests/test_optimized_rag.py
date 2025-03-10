# tests/test_optimized_rag.py
import sys
from pathlib import Path

import pytest_asyncio

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from src.rag.optimized_rag import OptimizedRecipeRAG
import time
import psutil
from dotenv import load_dotenv

# pytest.asyncio 설정
def pytest_configure(config):
    config.addinivalue_line(
        "asyncio_mode",
        "strict"
    )

# 테스트 설정
@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """전체 테스트 세션동안 사용할 이벤트 루프 생성"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    
    # 안전하게 루프 종료
    try:
        # 남은 태스크 처리
        for task in asyncio.all_tasks(loop):
            if not task.done() and not task.cancelled():
                task.cancel()
                
        # 작업 완료 대기
        if not loop.is_closed():
            loop.run_until_complete(asyncio.sleep(0.1))
            loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception as e:
        print(f"Event loop cleanup error: {e}")
    finally:
        if not loop.is_closed():
            loop.close()

@pytest_asyncio.fixture(scope="session")
async def rag_system():
    from src.rag.optimized_rag import OptimizedRecipeRAG
    # 이벤트 루프 확인
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    rag = OptimizedRecipeRAG(max_concurrent=3)
    rag.request_handler.rate_limit = 0.1  # 테스트용 rate limit 설정
    await rag.setup()
    yield rag
    try:
        await rag.cleanup()
    except Exception as e:
        print(f"Cleanup error: {e}")

@pytest.fixture
def test_questions():
    return [
        "김치찌개 레시피 알려줘",
        "된장찌개 만드는 방법 알려줘",
        "초보자도 쉽게 만들 수 있는 요리 추천해줘",
        "매운 음식을 덜 맵게 만드는 방법",
        "양파 대신 넣을 수 있는 재료 추천"
    ]

@pytest.mark.asyncio
async def test_cache_functionality(rag_system):
    """캐시 기능 테스트"""
    question = "김치찌개 레시피"
    
    response1 = await rag_system.ask_async(question)
    assert 'answer' in response1
    await asyncio.sleep(0.1)  # 캐시 저장 대기
    
    response2 = await rag_system.ask_async(question)
    assert 'answer' in response2
    assert response2.get('source') == 'cache'
    assert response2['execution_time'] < response1['execution_time']


@pytest.mark.asyncio
async def test_quality_metrics(rag_system):
   """품질 메트릭 계산 테스트"""
   question = "김치찌개 레시피"
   response = await rag_system.ask_async(question)
   
   assert 'quality_metrics' in response
   metrics = response['quality_metrics']
   assert all(key in metrics for key in ['completeness', 'relevance', 'structure'])
   assert all(0 <= metrics[key] <= 1 for key in metrics)

@pytest.mark.asyncio
async def test_error_handling(rag_system):
    """에러 처리 테스트"""
    response = await rag_system.ask_async("")  # 빈 질문
    assert 'answer' in response
    # completeness 대신 relevance로 검사
    assert response['quality_metrics']['relevance'] < 0.5  # 빈 입력이므로 낮은 관련성 점수를 기대

@pytest.mark.asyncio
async def test_concurrent_requests(rag_system):
   """동시 요청 처리 테스트"""
   questions = ["김치찌개", "된장찌개", "부대찌개"]
   tasks = [rag_system.ask_async(q) for q in questions]
   responses = await asyncio.gather(*tasks)
   
   assert len(responses) == len(questions)
   assert all('answer' in r for r in responses)

@pytest.mark.asyncio
async def test_rate_limiting(rag_system):
    """Rate limiting 테스트"""
    question = "간단한 레시피"
    start_time = time.time()
    
    tasks = [rag_system.ask_async(question) for _ in range(3)]
    responses = await asyncio.gather(*tasks)
    
    execution_time = time.time() - start_time
    assert execution_time >= 0.2  # rate limiting 확인
    assert all('answer' in r for r in responses)

@pytest.mark.asyncio
async def test_batch_processing(rag_system, test_questions):
    """배치 처리 테스트"""
    # TaskGroup 대신 gather 사용
    tasks = [rag_system.ask_async(q) for q in test_questions]
    responses = await asyncio.gather(*tasks)
    
    assert len(responses) == len(test_questions)
    assert all('answer' in r for r in responses)
    assert all('quality_metrics' in r for r in responses)

@pytest.mark.asyncio
async def test_memory_usage(rag_system):
   """메모리 사용량 테스트"""
   process = psutil.Process()
   initial_memory = process.memory_info().rss / 1024 / 1024
   
   question = "간단한 레시피"
   await rag_system.ask_async(question)
   
   final_memory = process.memory_info().rss / 1024 / 1024
   memory_increase = final_memory - initial_memory
   
   assert memory_increase < 500  # 메모리 증가량 500MB 이하

@pytest.mark.asyncio
async def test_response_time(rag_system):
    """응답 시간 테스트"""
    question = "간단한 레시피 추천"
    start_time = time.time()
    
    response = await rag_system.ask_async(question)
    execution_time = time.time() - start_time
    
    assert execution_time < 20  # 시간 제한
    assert 'answer' in response
    assert len(response['answer']) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=strict"])