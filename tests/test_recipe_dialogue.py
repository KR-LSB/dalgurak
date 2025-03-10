import sys
from pathlib import Path
import json
import time
import pytest
import asyncio
from datetime import datetime

# 프로젝트 루트 디렉토리 설정
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 필요한 모듈 임포트
from src.rag.optimized_rag import OptimizedRecipeRAG
from dotenv import load_dotenv


class TestRecipeDialogue:
    """요리 어시스턴트 문답 기능 테스트 클래스"""
    
    @classmethod
    def setup_class(cls):
        """테스트 클래스 초기화"""
        print("\n=== 요리 어시스턴트 문답 테스트 시작 ===")
        load_dotenv()
        
        # RAG 시스템 초기화
        cls.rag = OptimizedRecipeRAG()
        
        # 결과 저장 디렉토리 설정
        cls.results_dir = project_root / "tests" / "results"
        cls.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 테스트 결과 저장용 리스트
        cls.test_results = []
    
    @classmethod
    def teardown_class(cls):
        """테스트 클래스 종료"""
        # 테스트 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = cls.results_dir / f"dialogue_test_results_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(cls.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n테스트 결과가 {result_file}에 저장되었습니다.")
        print("=== 요리 어시스턴트 문답 테스트 종료 ===")
    
    def test_basic_recipe_queries(self):
        """기본 레시피 질문 테스트"""
        test_cases = [
            "김치찌개 레시피 알려줘",
            "간단한 된장찌개 만드는 방법 알려줘",
            "초보자도 쉽게 만들 수 있는 요리 추천해줘",
            "아이들이 좋아하는 간식 추천해줘"
        ]
        
        for query in test_cases:
            self._run_query_test(query, "basic_recipe")
    
    def test_ingredient_substitution(self):
        """재료 대체 질문 테스트"""
        test_cases = [
            "양파 대신 사용할 수 있는 재료는 뭐가 있을까?",
            "고춧가루가 없을 때 대체할 수 있는 재료 추천해줘",
            "설탕 대신 꿀을 사용해도 될까?",
            "버터 대신 사용할 수 있는 건강한 대체품 추천해줘"
        ]
        
        for query in test_cases:
            self._run_query_test(query, "ingredient_substitution")
    
    def test_cooking_techniques(self):
        """요리 기술 질문 테스트"""
        test_cases = [
            "찜기 없이 찜요리 하는 방법 알려줘",
            "고기를 부드럽게 만드는 방법은?",
            "볶음밥이 잘 들러붙지 않게 하려면 어떻게 해야 해?",
            "냄비 없이 라면 끓이는 방법 알려줘"
        ]
        
        for query in test_cases:
            self._run_query_test(query, "cooking_technique")
    
    def test_multi_turn_conversation(self):
        """멀티턴 대화 테스트"""
        conversation = [
            ("김치찌개 만드는 방법 알려줘", "initial_query"),
            ("재료를 좀 더 자세히 알려줄래?", "followup_ingredients"),
            ("양념은 어떻게 만들어?", "followup_seasoning"),
            ("아이도 먹을 수 있게 덜 맵게 만들려면?", "followup_modification")
        ]
        
        for i, (query, label) in enumerate(conversation):
            result = self._run_query_test(query, f"conversation_turn_{i+1}_{label}")
            # 1초 대기하여 자연스러운 대화 흐름 시뮬레이션
            time.sleep(1)
    
    def test_error_handling(self):
        """오류 처리 테스트"""
        test_cases = [
            ("", "empty_query"),
            ("###", "nonsense_query"),
            ("Tell me a recipe in English", "foreign_language"),
            ("레시피 알려줘" * 50, "very_long_query")
        ]
        
        for query, label in test_cases:
            self._run_query_test(query, f"error_{label}")
    
    @pytest.mark.asyncio
    async def test_async_batch_queries(self):
        """비동기 배치 쿼리 테스트"""
        test_cases = [
            "비빔밥 레시피 알려줘",
            "불고기 양념 비율 알려줘",
            "식혜 만드는 법 알려줘",
            "떡볶이 소스 레시피 알려줘",
            "파전 만드는 방법 알려줘"
        ]
        
        # 배치 실행
        start_time = time.time()
        tasks = [self.rag.ask_async(query) for query in test_cases]
        responses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # 결과 저장
        batch_results = {
            "test_type": "async_batch",
            "timestamp": datetime.now().isoformat(),
            "total_time": total_time,
            "queries": test_cases,
            "response_count": len(responses),
            "success_rate": sum(1 for r in responses if 'error' not in r) / len(responses)
        }
        
        self.test_results.append(batch_results)
        
        # 개별 응답 로깅
        for i, (query, response) in enumerate(zip(test_cases, responses)):
            result = {
                "query": query,
                "response_preview": response.get('answer', '')[:100] + '...' if response.get('answer') else None,
                "has_error": 'error' in response,
                "quality_metrics": response.get('quality_metrics', {})
            }
            print(f"\n[배치 쿼리 {i+1}] {query}")
            print(f"응답: {result['response_preview']}")
            print(f"품질 점수: {result['quality_metrics']}")
    
    def _run_query_test(self, query, label):
        """단일 쿼리 테스트 실행 헬퍼 메서드"""
        print(f"\n테스트 [{label}]: '{query}'")
        
        start_time = time.time()
        response = self.rag.ask(query)
        execution_time = time.time() - start_time
        
        # 결과 요약
        result = {
            "test_id": f"{label}_{int(time.time())}",
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time
        }
        
        # 응답 내용 요약
        if isinstance(response, dict):
            result.update({
                "response_preview": response.get('answer', '')[:100] + '...' if response.get('answer') else None,
                "response_length": len(response.get('answer', '')),
                "source": response.get('source', 'direct'),
                "quality_metrics": response.get('quality_metrics', {}),
                "has_error": 'error' in response
            })
            
            print(f"응답: {result['response_preview']}")
            print(f"응답 시간: {execution_time:.2f}초")
            print(f"품질 점수: {result['quality_metrics']}")
            print(f"소스: {result['source']}")
            
            if 'error' in response:
                print(f"오류: {response['error']}")
        else:
            result.update({
                "error": f"Invalid response type: {type(response)}"
            })
            print(f"오류: 유효하지 않은 응답 타입: {type(response)}")
        
        # 결과 저장
        self.test_results.append(result)
        return result


class TestAdvancedDialogueScenarios:
    """고급 대화 시나리오 테스트 클래스"""
    
    @classmethod
    def setup_class(cls):
        """테스트 클래스 초기화"""
        print("\n=== 고급 대화 시나리오 테스트 시작 ===")
        load_dotenv()
        
        # RAG 시스템 초기화
        cls.rag = OptimizedRecipeRAG()
        
        # 결과 저장 디렉토리 설정
        cls.results_dir = project_root / "tests" / "results"
        cls.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 테스트 결과 저장용 리스트
        cls.scenario_results = []
    
    @classmethod
    def teardown_class(cls):
        """테스트 클래스 종료"""
        # 테스트 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = cls.results_dir / f"advanced_dialogue_results_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(cls.scenario_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n테스트 결과가 {result_file}에 저장되었습니다.")
        print("=== 고급 대화 시나리오 테스트 종료 ===")
    
    def test_guided_cooking_scenario(self):
        """요리 가이드 시나리오 테스트"""
        scenario = [
            "오늘 저녁으로 간단한 요리 추천해줘",
            "그중에서 김치찌개 레시피 알려줘",
            "재료는 뭐가 필요해?",
            "양념은 어떻게 만들어?",
            "육수는 어떻게 우려내?",
            "끓이는 시간은 얼마나 돼?",
            "밥과 함께 먹을 반찬 추천해줘"
        ]
        
        self._run_scenario_test(scenario, "guided_cooking")
    
    def test_dietary_restriction_scenario(self):
        """식이 제한 시나리오 테스트"""
        scenario = [
            "채식주의자를 위한 요리 추천해줘",
            "고기 없이 단백질을 충분히 섭취할 수 있는 요리는?",
            "두부로 만들 수 있는 요리 알려줘",
            "그 중에서 두부 스테이크 레시피 알려줘",
            "달걀 대신 사용할 수 있는 식물성 재료는?",
            "설탕 대신 건강한 감미료 추천해줘"
        ]
        
        self._run_scenario_test(scenario, "dietary_restriction")
    
    def test_cooking_troubleshooting_scenario(self):
        """요리 문제 해결 시나리오 테스트"""
        scenario = [
            "요리할 때 자주 실수하는 부분이 뭐야?",
            "소금을 너무 많이 넣었을 때 해결 방법은?",
            "국물이 너무 싱거울 때 간을 맞추는 비법은?",
            "고기가 질겨졌을 때 부드럽게 만드는 방법은?",
            "튀김옷이 잘 입혀지지 않을 때는 어떻게 해?",
            "눌어붙은 냄비 쉽게 세척하는 방법 알려줘"
        ]
        
        self._run_scenario_test(scenario, "troubleshooting")
    
    def _run_scenario_test(self, scenario_queries, scenario_name):
        """시나리오 테스트 실행 헬퍼 메서드"""
        print(f"\n=== 시나리오 테스트: {scenario_name} ===")
        
        scenario_result = {
            "scenario_name": scenario_name,
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(scenario_queries),
            "dialogue_turns": []
        }
        
        start_scenario_time = time.time()
        
        for i, query in enumerate(scenario_queries):
            print(f"\n[턴 {i+1}] 사용자: {query}")
            
            # 응답 생성
            start_time = time.time()
            response = self.rag.ask(query)
            execution_time = time.time() - start_time
            
            # 턴 결과 저장
            turn_result = {
                "turn": i+1,
                "query": query,
                "execution_time": execution_time
            }
            
            if isinstance(response, dict):
                answer = response.get('answer', '')
                turn_result.update({
                    "response": answer,
                    "response_length": len(answer),
                    "quality_metrics": response.get('quality_metrics', {}),
                    "has_error": 'error' in response
                })
                
                print(f"어시스턴트: {answer[:150]}..." if len(answer) > 150 else f"어시스턴트: {answer}")
                print(f"응답 시간: {execution_time:.2f}초")
                print(f"품질 점수: {turn_result['quality_metrics']}")
                
                if 'error' in response:
                    print(f"오류: {response['error']}")
                    turn_result["error"] = response['error']
            else:
                turn_result["error"] = f"Invalid response type: {type(response)}"
                print(f"오류: 유효하지 않은 응답 타입: {type(response)}")
            
            scenario_result["dialogue_turns"].append(turn_result)
            
            # 자연스러운 대화 흐름을 위한 딜레이
            time.sleep(1)
        
        # 시나리오 완료 통계
        scenario_result["total_time"] = time.time() - start_scenario_time
        scenario_result["avg_response_time"] = sum(turn["execution_time"] for turn in scenario_result["dialogue_turns"]) / len(scenario_queries)
        scenario_result["success_rate"] = sum(1 for turn in scenario_result["dialogue_turns"] if not turn.get("has_error", False)) / len(scenario_queries)
        
        # 대화 일관성 점수 계산
        scenario_result["coherence_score"] = self._calculate_coherence_score(scenario_result["dialogue_turns"])
        
        print(f"\n=== 시나리오 결과 ===")
        print(f"총 소요 시간: {scenario_result['total_time']:.2f}초")
        print(f"평균 응답 시간: {scenario_result['avg_response_time']:.2f}초")
        print(f"성공률: {scenario_result['success_rate']:.2%}")
        print(f"대화 일관성 점수: {scenario_result['coherence_score']:.2f}/5.0")
        
        # 결과 저장
        self.scenario_results.append(scenario_result)
    
    def _calculate_coherence_score(self, dialogue_turns):
        """대화 일관성 점수 계산 (간단한 휴리스틱 기반)"""
        if len(dialogue_turns) < 2:
            return 5.0  # 단일 턴은 일관성 문제 없음
        
        # 기본 점수 시작
        score = 5.0
        
        # 대화 흐름 분석
        for i in range(1, len(dialogue_turns)):
            current_turn = dialogue_turns[i]
            previous_turn = dialogue_turns[i-1]
            
            # 오류 발생 시 감점
            if current_turn.get("has_error", False):
                score -= 1.0
                continue
                
            current_response = current_turn.get("response", "")
            previous_response = previous_turn.get("response", "")
            
            # 연속된 응답의 품질 점수가 크게 떨어지면 감점
            current_quality = current_turn.get("quality_metrics", {})
            previous_quality = previous_turn.get("quality_metrics", {})
            
            if current_quality and previous_quality:
                if current_quality.get("relevance", 1) < previous_quality.get("relevance", 1) - 0.3:
                    score -= 0.5
                
                if current_quality.get("completeness", 1) < previous_quality.get("completeness", 1) - 0.3:
                    score -= 0.5
            
            # 이전 질문에 대한 참조가 있는지 확인
            if not any(keyword in current_response.lower() for keyword in
                      ["이전", "질문", "말씀", "언급", "앞서", "요청"]):
                score -= 0.2
        
        # 최종 점수 범위 조정
        return max(1.0, min(5.0, score))


def run_dialogue_tests():
    """대화 테스트 실행 함수"""
    pytest.main(["-xvs", __file__])


if __name__ == "__main__":
    run_dialogue_tests()