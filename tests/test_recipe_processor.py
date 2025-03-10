import sys
import json
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.processing.recipe_processor import RecipeProcessor

def test_recipe_processor():
    # 데이터 경로 설정
    data_dir = Path('data/raw/recipes_detailed_20250117_021548')
    
    # RecipeProcessor 인스턴스 생성
    processor = RecipeProcessor()
    
    try:
        # 모든 배치 파일 처리
        all_recipes = []
        batch_files = sorted(data_dir.glob('recipes_batch_*.json'))
        
        if not batch_files:
            print("레시피 배치 파일을 찾을 수 없습니다.")
            return
            
        print(f"총 {len(batch_files)}개의 배치 파일 발견")
        
        for batch_file in batch_files:
            print(f"Processing batch file: {batch_file.name}")
            # JSON 파일 읽기
            with open(batch_file, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
            # 레시피 처리
            processed_recipes = processor.process_recipes(recipes)
            all_recipes.extend(processed_recipes)
            print(f"- {len(processed_recipes)}개의 레시피 처리 완료")
        
        # 처리된 데이터 저장
        processor.save_processed_recipes(all_recipes)
        
        print(f"\n총 처리된 레시피 수: {len(all_recipes)}")
        
    except Exception as e:
        print(f"에러 발생: {str(e)}")
        raise  # 상세한 에러 메시지를 보기 위해 예외를 다시 발생시킴

if __name__ == "__main__":
    test_recipe_processor()