import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.embedding.recipe_embedder import RecipeEmbedder

def test_recipe_embedder():
    # MongoDB 데이터 파일 찾기
    processed_dir = project_root / 'data' / 'processed'
    mongo_files = list(processed_dir.glob('mongo_recipes_*.json'))
    
    if not mongo_files:
        print("MongoDB 데이터 파일을 찾을 수 없습니다.")
        return
        
    latest_file = max(mongo_files, key=lambda x: x.stat().st_mtime)
    print(f"임베딩할 파일: {latest_file}")
    
    # 데이터 로드
    with open(latest_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    print(f"총 {len(recipes)}개의 레시피 임베딩 시작")
    
    # 임베딩 실행
    embedder = RecipeEmbedder()
    vectordb = embedder.create_vector_store(recipes)

if __name__ == "__main__":
    test_recipe_embedder()