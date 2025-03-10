# tests/test_recipe_statistics.py
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processing.recipe_statistics import RecipeStatistics

def test_recipe_statistics():
    # MongoDB 데이터 파일 찾기
    processed_dir = project_root / 'data' / 'processed'
    mongo_files = list(processed_dir.glob('mongo_recipes_*.json'))
    
    if not mongo_files:
        print("MongoDB 데이터 파일을 찾을 수 없습니다.")
        return
        
    latest_file = max(mongo_files, key=lambda x: x.stat().st_mtime)
    print(f"분석할 파일: {latest_file}")
    
    # 데이터 로드
    with open(latest_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    # 통계 분석 실행
    analyzer = RecipeStatistics()
    stats = analyzer.analyze_recipes(recipes)
    
    # 시각화 생성
    analyzer.generate_visualizations()
    
    # 결과 저장
    analyzer.save_statistics()

if __name__ == "__main__":
    test_recipe_statistics()