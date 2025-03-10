import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.recipe_rag import RecipeRAG

def test_recipe_rag():
    rag = RecipeRAG()
    
    # 테스트 질문들
    test_questions = [
            ("", "empty_query"),
            ("###", "nonsense_query"),
            ("Tell me a recipe in English", "foreign_language"),
            ("레시피 알려줘" * 50, "very_long_query")
    ]
    
    
    print("\n=== RAG 시스템 테스트 ===")
    for question in test_questions:
        print(f"\n질문: {question}")
        answer = rag.ask(question)
        print(f"답변: {answer}")
        print("-" * 50)



if __name__ == "__main__":
    test_recipe_rag()