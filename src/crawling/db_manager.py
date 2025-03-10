from pymongo import MongoClient
import json
from pathlib import Path
from dotenv import load_dotenv
import os

class RecipeDB:
    def __init__(self):
        try:
            load_dotenv()
            username = os.getenv('MONGODB_USERNAME')
            password = os.getenv('MONGODB_PASSWORD')
            cluster = os.getenv('MONGODB_CLUSTER')
            
            self.uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=lsb"
            
            print("Connecting with URI:", self.uri.replace(self.uri.split(':')[2].split('@')[0], '****'))
            
            self.client = MongoClient(self.uri)
            self.db = self.client['recipe_db']
            self.recipes = self.db['recipes']
        except Exception as e:
            print(f"초기화 중 오류 발생: {e}")
            raise
    
    def test_connection(self):
        """데이터베이스 연결 테스트"""
        try:
            # 서버 정보 출력으로 연결 테스트
            server_info = self.client.server_info()
            print("MongoDB 연결 성공!")
            print(f"서버 버전: {server_info.get('version')}")
            
            # 데이터베이스 접근 권한 테스트
            dbs = self.client.list_database_names()
            print(f"접근 가능한 데이터베이스: {dbs}")
            return True
        except Exception as e:
            print(f"MongoDB 연결 실패: {e}")
            print(f"에러 타입: {type(e).__name__}")
            return False
    
    def import_json_data(self, json_file: Path):
        """JSON 파일 데이터를 MongoDB에 가져오기"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
                
            if isinstance(recipes, list):
                result = self.recipes.insert_many(recipes)
                print(f"{len(result.inserted_ids)}개의 레시피 추가 완료")
            else:
                result = self.recipes.insert_one(recipes)
                print("1개의 레시피 추가 완료")
                
        except Exception as e:
            print(f"데이터 가져오기 실패: {e}")



def main():
    db = RecipeDB()
    if db.test_connection():
        # 대상 디렉토리 경로
        recipe_dir = Path('/Users/iseungbyeong/Projects/dalgurak-ai/data/raw/recipes_detailed_20250117_021548')
        
        if recipe_dir.is_dir():
            # 디렉토리 내의 모든 JSON 파일 찾기
            json_files = list(recipe_dir.glob('*.json'))
            
            if json_files:
                for json_file in json_files:
                    print(f"\n파일 발견: {json_file.name}")
                    db.import_json_data(json_file)
            else:
                print(f"\nJSON 파일을 찾을 수 없습니다.")
                print("디렉토리 내 파일 목록:")
                for file in recipe_dir.iterdir():
                    print(f"- {file.name}")
        else:
            print(f"\n디렉토리를 찾을 수 없습니다: {recipe_dir}")

if __name__ == "__main__":
    main()