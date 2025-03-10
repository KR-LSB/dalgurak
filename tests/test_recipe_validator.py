# tests/test_recipe_validator.py
import sys
from pathlib import Path
import json

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processing.recipe_validator import RecipeValidator

def test_recipe_validator():
    # 프로젝트 루트 기준으로 데이터 디렉토리 경로 설정
    processed_dir = project_root / 'data' / 'processed'
    mongo_files = list(processed_dir.glob('mongo_recipes_*.json'))
    
    if not mongo_files:
        print(f"MongoDB 데이터 파일을 찾을 수 없습니다. (검색 경로: {processed_dir})")
        return
        
    latest_file = max(mongo_files, key=lambda x: x.stat().st_mtime)
    print(f"검증할 파일: {latest_file}")
    
    # 데이터 로드
    with open(latest_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    # 검증 실행
    validator = RecipeValidator()
    validation_results = validator.validate_recipes(recipes)
    
    # 결과 저장
    validator.save_validation_results()

if __name__ == "__main__":
    test_recipe_validator()