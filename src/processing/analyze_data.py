import sys
from pathlib import Path
from pymongo import MongoClient
from recipe_processor import RecipeProcessor
from recipe_validator import RecipeValidator
from recipe_statistics import RecipeStatistics
from dotenv import load_dotenv
import os

def fetch_recipes_from_mongodb():
    """MongoDB에서 레시피 데이터 가져오기"""
    try:
        # .env 파일에서 환경 변수 로드
        load_dotenv()
        
        # MongoDB 연결 정보
        username = os.getenv('MONGODB_USERNAME')
        password = os.getenv('MONGODB_PASSWORD')
        cluster = os.getenv('MONGODB_CLUSTER')
        uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=lsb"
        
        # MongoDB 연결
        client = MongoClient(uri)
        db = client['recipe_db']
        recipes = db['recipes']
        
        # 모든 레시피 가져오기
        all_recipes = list(recipes.find({}))
        
        # ObjectId 처리
        for recipe in all_recipes:
            recipe['_id'] = str(recipe['_id'])
            
        print(f"MongoDB에서 {len(all_recipes)}개의 레시피를 가져왔습니다.")
        return all_recipes
        
    except Exception as e:
        print(f"MongoDB 데이터 가져오기 실패: {str(e)}")
        return None

def main():
    # 1. MongoDB에서 데이터 가져오기
    print("MongoDB에서 데이터 로드 중...")
    recipes = fetch_recipes_from_mongodb()
    if not recipes:
        print("데이터 로드 실패")
        return

    # 2. 데이터 전처리
    print("\n데이터 전처리 시작...")
    processor = RecipeProcessor()
    processed_recipes = processor.process_recipes(recipes)
    
    # None 값 필터링
    valid_recipes = [recipe for recipe in processed_recipes if recipe is not None]
    print(f"\n유효한 레시피 수: {len(valid_recipes)} / 전체: {len(processed_recipes)}")
    
    # 처리된 데이터 저장
    processed_dir = Path('data/processed')
    processed_dir.mkdir(parents=True, exist_ok=True)
    processor.save_processed_recipes(valid_recipes, processed_dir)

    # 3. 데이터 검증
    print("\n데이터 검증 시작...")
    validator = RecipeValidator()
    validation_results = validator.validate_recipes(valid_recipes)
    
    # 검증 결과 저장
    validation_dir = Path('data/validation')
    validation_dir.mkdir(parents=True, exist_ok=True)
    validator.save_validation_results(validation_dir)

    # 4. 통계 분석
    print("\n통계 분석 시작...")
    stats = RecipeStatistics()
    analysis_results = stats.analyze_recipes(valid_recipes)
    
    # 통계 결과 저장
    stats_dir = Path('data/statistics')
    stats_dir.mkdir(parents=True, exist_ok=True)
    stats.save_statistics(stats_dir)
    
    # 시각화 생성
    visualization_dir = stats_dir / 'visualizations'
    visualization_dir.mkdir(parents=True, exist_ok=True)
    stats.generate_visualizations(visualization_dir)

if __name__ == "__main__":
    main()