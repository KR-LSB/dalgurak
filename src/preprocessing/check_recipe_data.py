from pathlib import Path
import json

def check_recipe_data():
    # 데이터 디렉토리 설정
    project_root = Path(__file__).parent.parent.parent
    raw_data_dir = project_root / 'data' / 'raw'
    
    # 가장 최신 detailed 디렉토리 찾기
    latest_dir = sorted(raw_data_dir.glob('recipes_detailed_*'))[-1]
    
    # 첫 번째 배치 파일 확인
    first_batch = sorted(latest_dir.glob('recipes_batch_*.json'))[0]
    
    with open(first_batch, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
        
    # 첫 번째 레시피의 데이터 구조 출력
    first_recipe = recipes[0]
    print("=== 레시피 데이터 구조 ===")
    print(json.dumps(first_recipe, ensure_ascii=False, indent=2))
    
    # 재료 정보 구조 확인
    print("\n=== 재료 정보 구조 ===")
    ingredients = first_recipe.get('ingredients', [])
    if ingredients:
        print(f"재료 개수: {len(ingredients)}")
        print("첫 번째 재료:", json.dumps(ingredients[0], ensure_ascii=False, indent=2))
        
if __name__ == "__main__":
    check_recipe_data()