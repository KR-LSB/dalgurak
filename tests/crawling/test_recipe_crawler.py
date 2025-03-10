import sys
from pathlib import Path
import logging
from datetime import datetime
import json
import traceback
from typing import Dict, List
import time

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.crawling.recipe_collectors import NaverRecipeCollector, UNIFIED_CATEGORIES

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'test_crawling_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_test_directories() -> Dict[str, Path]:
    """테스트용 디렉토리 설정"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    dirs = {
        'base': Path('data/test'),
        'raw': Path(f'data/test/raw/recipes_detailed_{timestamp}'),
        'processed': Path(f'data/test/processed/recipes_{timestamp}'),
        'progress': Path('data/test/progress')
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"테스트 디렉토리 생성: {dir_path}")
    
    return dirs

#!/usr/bin/env python3
# ... (이전 임포트 부분 동일) ...

def format_ingredient(ingredient: Dict) -> str:
    """재료 정보를 보기 좋게 포맷팅"""
    amount = ingredient.get('amount', {})
    amount_str = f"{amount.get('value', '')} {amount.get('unit', '')}" if amount else ""
    return f"{ingredient.get('name', '')}: {amount_str} ({ingredient.get('section', '')})"

def test_recipe_collection(pages_per_category: int = 1, recipes_per_category: int = 5):
    """레시피 수집 테스트"""
    dirs = setup_test_directories()
    collector = NaverRecipeCollector()
    test_results = {
        'total_tested': 0,
        'successful': 0,
        'failed': 0,
        'errors': [],
        'category_results': {}
    }
    
    try:
        for category_key, category_data in UNIFIED_CATEGORIES.items():
            category_name = category_data['name']
            logger.info(f"\n{'='*50}")
            logger.info(f"테스트 카테고리: {category_name}")
            logger.info('='*50)
            
            try:
                # URL 수집 (카테고리당 5개만)
                recipes = collector.get_recipe_urls_from_category(
                    category_name, 
                    pages=pages_per_category
                )[:recipes_per_category]
                
                logger.info(f"수집된 URL 수: {len(recipes)}")
                
                category_results = {
                    'total': len(recipes),
                    'success': 0,
                    'failed': 0,
                    'recipes': []
                }
                
                # 상세 정보 크롤링
                for recipe_info in recipes:
                    try:
                        logger.info(f"\n------- 레시피: {recipe_info['title']} -------")
                        recipe = collector.crawl_recipe(recipe_info['url'])
                        
                        if recipe and recipe.get('ingredients'):
                            # 재료 정보 검증
                            valid_ingredients = [
                                ing for ing in recipe['ingredients']
                                if ing.get('name') and 
                                not ing['name'].startswith('요리') and
                                not ing['name'] in ['주재료', '부재료', '양념', '재료설명', '조리시간', '분량']
                            ]
                            
                            recipe['ingredients'] = valid_ingredients
                            
                            # 재료 정보 출력
                            logger.info("\n▶ 재료 목록:")
                            
                            # 섹션별로 재료 그룹화
                            ingredients_by_section = {}
                            for ing in valid_ingredients:
                                section = ing.get('section', '기타')
                                if section not in ingredients_by_section:
                                    ingredients_by_section[section] = []
                                ingredients_by_section[section].append(ing)
                            
                            # 섹션별로 출력
                            for section, ingredients in ingredients_by_section.items():
                                logger.info(f"\n[{section}]")
                                for ing in ingredients:
                                    logger.info(f"  • {format_ingredient(ing)}")
                            
                            # 조리 단계 출력
                            if recipe.get('steps'):
                                logger.info("\n▶ 조리 단계:")
                                for step in recipe['steps']:
                                    logger.info(f"  {step['step_num']}. {step['description']}")
                            
                            # 결과 저장
                            category_results['recipes'].append({
                                'title': recipe['title'],
                                'url': recipe['url'],
                                'ingredients_count': len(valid_ingredients),
                                'steps_count': len(recipe.get('steps', [])),
                                'ingredients': valid_ingredients
                            })
                            
                            logger.info(f"\n✓ 성공: 재료 {len(valid_ingredients)}개, 조리단계 {len(recipe.get('steps', []))}개")
                            category_results['success'] += 1
                            test_results['successful'] += 1
                        else:
                            logger.error("✗ 실패: 레시피 정보 없음")
                            category_results['failed'] += 1
                            test_results['failed'] += 1
                            
                    except Exception as e:
                        logger.error(f"✗ 오류: {str(e)}")
                        category_results['failed'] += 1
                        test_results['failed'] += 1
                        test_results['errors'].append(str(e))
                
                test_results['category_results'][category_name] = category_results
                
                # 결과 저장
                results_file = dirs['progress'] / f"test_results_{category_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(results_file, 'w', encoding='utf-8') as f:
                    json.dump(category_results, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                logger.error(f"카테고리 처리 중 오류: {str(e)}")
                test_results['errors'].append(str(e))
                continue
            
            # 진행 상황 출력
            success_rate = (category_results['success'] / category_results['total'] * 100 
                          if category_results['total'] > 0 else 0)
            logger.info(f"\n{category_name} 결과:")
            logger.info(f"성공률: {success_rate:.1f}% ({category_results['success']}/{category_results['total']})")
            
    except Exception as e:
        logger.error(f"테스트 중 치명적 오류: {str(e)}")
        logger.error(traceback.format_exc())
        
    finally:
        # 최종 결과 출력
        logger.info("\n" + "="*50)
        logger.info("테스트 최종 결과")
        logger.info("="*50)
        logger.info(f"총 테스트: {test_results['successful'] + test_results['failed']}")
        logger.info(f"성공: {test_results['successful']}")
        logger.info(f"실패: {test_results['failed']}")
        
        if test_results['errors']:
            logger.info("\n주요 오류:")
            for error in set(test_results['errors']):
                logger.info(f"- {error}")
                
        logger.info("\n카테고리별 결과:")
        for category, results in test_results['category_results'].items():
            success_rate = (results['success'] / results['total'] * 100 
                          if results['total'] > 0 else 0)
            logger.info(f"\n{category}:")
            logger.info(f"성공률: {success_rate:.1f}% ({results['success']}/{results['total']})")
            
            if results.get('recipes'):
                logger.info("성공한 레시피:")
                for recipe in results['recipes']:
                    logger.info(f"\n- {recipe['title']}")
                    logger.info(f"  재료 {recipe['ingredients_count']}개, 조리단계 {recipe['steps_count']}개")

def main():
    """메인 테스트 함수"""
    start_time = time.time()
    logger.info("=== 레시피 수집 테스트 시작 ===")
    
    try:
        test_recipe_collection(pages_per_category=2, recipes_per_category=5)
    except Exception as e:
        logger.error(f"테스트 실행 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"\n총 소요 시간: {elapsed_time/60:.1f}분")
        logger.info("=== 테스트 완료 ===")

if __name__ == "__main__":
    main()