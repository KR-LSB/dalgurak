import sys
from pathlib import Path
from pymongo import MongoClient
import json
from datetime import datetime
from dotenv import load_dotenv
import os

def fetch_recipes_from_mongodb():
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
        
        # 저장 경로 설정
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / 'data' / 'processed'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        output_file = output_dir / f'mongo_recipes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_recipes, f, ensure_ascii=False, indent=2)
            
        print(f"데이터를 {output_file}에 저장했습니다.")
        
        return all_recipes
        
    except Exception as e:
        print(f"MongoDB 데이터 가져오기 실패: {str(e)}")
        return None

if __name__ == "__main__":
    recipes = fetch_recipes_from_mongodb()
    if recipes:
        print("\n=== 데이터 저장 경로 ===")
        print(f"프로젝트 루트: {Path(__file__).parent.parent.parent}")
        print(f"데이터 저장 경로: {Path(__file__).parent.parent.parent / 'data' / 'processed'}")