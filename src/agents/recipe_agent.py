import sys
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from crawling.recipe_collectors import TenThousandRecipeCollector, NaverRecipeCollector
from src.processing.recipe_processor import RecipeProcessor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recipe_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def collect_recipe_urls():
    """레시피 URL 수집"""
    collectors = {
        TenThousandRecipeCollector(): 6500,  # 목표 수집량 설정
        NaverRecipeCollector(): 3500
    }
    all_recipes = []
    
    try:
        for collector, target_count in collectors.items():
            logger.info(f"Starting collection for {collector.__class__.__name__} (target: {target_count})")
            
            # 더 많은 페이지 수집을 위해 페이지 수 증가
            recipes = collector.collect_recipes(
                pages_per_category=50,  # 페이지 수 증가
                include_situations=True  # 상황별 레시피도 포함
            )
            
            # 목표 수량에 맞게 조정
            if len(recipes) > target_count:
                logger.info(f"Collected {len(recipes)} recipes, trimming to target {target_count}")
                recipes = recipes[:target_count]
                
            # 수집된 레시피 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recipe_urls_{collector.__class__.__name__}_{timestamp}.json"
            collector.save_recipes(recipes, filename)
            
            all_recipes.extend(recipes)
            logger.info(f"Collected {len(recipes)} recipes from {collector.__class__.__name__}")
            
        return all_recipes
    except Exception as e:
        logger.error(f"Error during URL collection: {e}", exc_info=True)
        raise
    finally:
        for collector in collectors.keys():
            if hasattr(collector, 'driver'):
                collector.driver.quit()
                logger.info(f"Cleaned up driver for {collector.__class__.__name__}")

def crawl_recipe_details(urls_file: str = None, batch_size: int = 100):
    """수집된 URL에서 상세 레시피 정보 크롤링"""
    data_dir = Path(project_root) / 'data'
    raw_dir = data_dir / 'raw'
    
    try:
        # URL 파일 찾기
        if urls_file is None:
            json_files = list(raw_dir.glob('recipe_urls_*.json'))
            if not json_files:
                logger.error("No recipe URL files found")
                return
            urls_file = max(json_files, key=os.path.getctime)
        
        logger.info(f"Using URL file: {urls_file}")
        
        # URL 목록 로드
        with open(urls_file, 'r', encoding='utf-8') as f:
            recipe_infos = json.load(f)
        
        logger.info(f"Loaded {len(recipe_infos)} recipes from {urls_file}")
        
        # 결과 저장 디렉토리 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = raw_dir / f"recipes_detailed_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # URL 분류
        site_recipes = {
            '10000recipe.com': [],
            'terms.naver.com': []
        }
        
        for recipe in recipe_infos:
            for site in site_recipes:
                if site in recipe['url']:
                    site_recipes[site].append(recipe)
                    break
        
        logger.info(f"Classified URLs: {len(site_recipes['10000recipe.com'])} for 만개의레시피, "
                   f"{len(site_recipes['terms.naver.com'])} for 네이버 요리백과")
        
        # 만개의레시피 수집
        if site_recipes['10000recipe.com']:
            collector = TenThousandRecipeCollector()
            try:
                logger.info("Starting collection from 만개의레시피...")
                collector.crawl_recipes_batch(
                    site_recipes['10000recipe.com'], 
                    output_dir, 
                    batch_size=batch_size
                )
            except Exception as e:
                logger.error(f"Error during 만개의레시피 collection: {e}", exc_info=True)
            finally:
                if hasattr(collector, 'driver'):
                    collector.driver.quit()
                    logger.info("Cleaned up 만개의레시피 driver")
        
        # 네이버 요리백과 수집
        if site_recipes['terms.naver.com']:
            collector = NaverRecipeCollector()
            try:
                logger.info("Starting collection from 네이버 요리백과...")
                collector.crawl_recipes_batch(
                    site_recipes['terms.naver.com'], 
                    output_dir, 
                    batch_size=batch_size
                )
            except Exception as e:
                logger.error(f"Error during 네이버 요리백과 collection: {e}", exc_info=True)
        
        logger.info("Crawling completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during recipe detail crawling: {e}", exc_info=True)
        raise

def process_recipes():
    """수집된 레시피 데이터 처리"""
    try:
        processor = RecipeProcessor(Path(project_root) / 'data' / 'raw')
        
        logger.info("Starting recipe processing...")
        processor.process_all_recipes()
        
        # 처리된 데이터 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"processed_recipes_{timestamp}.json"
        processor.save_processed_data(filename)
        
        # 통계 계산 및 반환
        stats = processor.get_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Error during recipe processing: {e}", exc_info=True)
        raise

def main():
    start_time = time.time()
    logger.info("=== Recipe Collection Process Started ===")
    
    try:
        # 1. URL 수집
        logger.info("Step 1: Collecting recipe URLs...")
        recipes = collect_recipe_urls()
        
        if recipes:  # URL 수집 성공 확인
            # 수집된 URL 저장
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recipe_urls_{timestamp}.json"
            data_dir = Path('data/raw')
            data_dir.mkdir(parents=True, exist_ok=True)
            
            with open(data_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
            
            # 2. 상세 정보 크롤링
            logger.info("Step 2: Crawling recipe details...")
            crawl_recipe_details(str(data_dir / filename), batch_size=100)
            
            # 3. 데이터 처리
            logger.info("Step 3: Processing collected data...")
            processor = RecipeProcessor(data_dir)
            processor.process_all_recipes()
            stats = processor.get_statistics()
            
            # 4. 결과 출력
            logger.info("\n=== Collection Results ===")
            logger.info(f"총 레시피 수: {stats['total_recipes']:,}개")
            logger.info(f"평균 조리 단계: {stats['avg_steps']:.1f}단계")
            logger.info(f"평균 재료 수: {stats['avg_ingredients']:.1f}개")
            
            logger.info("\n카테고리별 분포:")
            for category, count in sorted(stats['categories'].items()):
                logger.info(f"- {category}: {count:,}개")
        else:
            logger.error("URL 수집 실패")
            
    except Exception as e:
        logger.error(f"Critical error in main process: {e}", exc_info=True)
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"\nTotal execution time: {elapsed_time/3600:.2f} hours")
        logger.info("=== Recipe Collection Process Completed ===")
        logger.info("Process finished")


if __name__ == "__main__":
    main()