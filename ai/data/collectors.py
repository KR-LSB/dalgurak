"""
레시피 데이터 수집기

만개의레시피, 네이버 요리백과에서 레시피 데이터 수집

Features:
    - Selenium 기반 동적 크롤링
    - robots.txt 준수
    - 배치 처리 및 진행 상황 저장
    - 재시도 로직 및 에러 처리
    - 통합 카테고리 매핑

Data Sources:
    - 만개의레시피 (10000recipe.com): 6,500+ 레시피
    - 네이버 요리백과 (terms.naver.com): 1,000+ 레시피

Example:
    >>> collector = TenThousandRecipeCollector()
    >>> recipes = collector.collect_recipes(pages_per_category=10)
    >>> collector.save_recipes(recipes)
"""

import atexit
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tqdm import tqdm

# Selenium은 선택적 임포트 (설치되지 않은 환경 대응)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import (
        TimeoutException,
        NoSuchElementException,
        WebDriverException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


logger = logging.getLogger(__name__)


# ============================================================
# 통합 카테고리 매핑
# ============================================================

UNIFIED_CATEGORIES = {
    "RICE_PORRIDGE": {
        "name": "밥/죽/떡",
        "categories": ["밥류", "죽류", "떡류", "한과"],
        "naver_ids": ["48196", "48197", "48221", "48222"],
        "tenthousand_query": ["밥"]
    },
    "NOODLE_DUMPLING": {
        "name": "면/만두",
        "categories": ["면류", "만두류", "스파게티/파스타"],
        "naver_ids": ["48198", "48199", "48217"],
        "tenthousand_query": ["면"]
    },
    "SOUP_STEW": {
        "name": "국/탕/찌개",
        "categories": ["국", "탕", "찌개", "전골"],
        "naver_ids": ["48200", "48201"],
        "tenthousand_query": ["국탕", "찌개"]
    },
    "SIDE_DISHES": {
        "name": "반찬",
        "categories": ["구이", "조림", "볶음", "무침", "튀김", "부침", "찜/삶기", "냉채"],
        "naver_ids": ["48202", "48203", "48204", "48205", "48206", "48207", "48208", "48209"],
        "tenthousand_query": ["밑반찬", "메인반찬"]
    },
    "PICKLE_SAUCE": {
        "name": "장아찌/김치/젓갈",
        "categories": ["김치", "젓갈", "장아찌", "피클"],
        "naver_ids": ["48210", "48211", "48212", "48213"],
        "tenthousand_query": ["김치젓갈장류"]
    },
    "WESTERN": {
        "name": "양식",
        "categories": ["샐러드", "수프", "피자", "스파게티/파스타", "스테이크"],
        "naver_ids": ["48214", "48215", "48216", "48217", "48218"],
        "tenthousand_query": ["양식"]
    },
    "SAUCE_SEASONING": {
        "name": "양념/장류",
        "categories": ["잼", "드레싱/소스", "장류", "조미료/향신료", "가루류"],
        "naver_ids": ["48219", "48220", "48234", "48235", "48236"],
        "tenthousand_query": ["양념소스잼"]
    },
    "BREAD_SNACK": {
        "name": "빵/과자",
        "categories": ["빵", "샌드위치/토스트", "과자", "무스/푸딩/크림"],
        "naver_ids": ["48223", "48224", "48225", "48226"],
        "tenthousand_query": ["빵", "과자"]
    },
    "BEVERAGE": {
        "name": "음료/차/술",
        "categories": ["커피", "차/다류", "주스", "건강음료", "스무디/쉐이크", "칵테일"],
        "naver_ids": ["48227", "48228", "48392", "48393", "48394", "48395"],
        "tenthousand_query": ["차음료술"]
    },
    "DAIRY": {
        "name": "유제품",
        "categories": ["치즈", "요구르트", "기타유제품"],
        "naver_ids": ["48403", "48404", "48233"],
        "tenthousand_query": ["유제품"]
    },
    "OTHERS": {
        "name": "기타",
        "categories": ["기타"],
        "naver_ids": ["48172"],
        "tenthousand_query": ["기타"]
    }
}


def map_category_name(
    category_id: Optional[str] = None,
    site_query: Optional[str] = None
) -> str:
    """
    카테고리 ID/쿼리를 통합 카테고리명으로 변환
    
    Args:
        category_id: 네이버 카테고리 ID
        site_query: 만개의레시피 검색 쿼리
        
    Returns:
        통합 카테고리명
    """
    if category_id:
        for category_data in UNIFIED_CATEGORIES.values():
            if category_id in category_data["naver_ids"]:
                return category_data["name"]
    elif site_query:
        for category_data in UNIFIED_CATEGORIES.values():
            if site_query in category_data["tenthousand_query"]:
                return category_data["name"]
    return UNIFIED_CATEGORIES["OTHERS"]["name"]


# ============================================================
# 베이스 수집기 클래스
# ============================================================

class BaseRecipeCollector(ABC):
    """
    레시피 수집 베이스 클래스
    
    모든 레시피 수집기의 공통 기능을 정의합니다:
    - robots.txt 준수
    - 진행 상황 자동 저장
    - 배치 처리
    - 재시도 로직
    
    상속 시 구현 필요:
    - setup_site_config(): 사이트별 설정
    - setup_categories(): 카테고리 설정
    - get_recipe_urls_from_category(): URL 수집
    - crawl_recipe(): 상세 크롤링
    - cleanup(): 리소스 정리
    """
    
    def __init__(self):
        self.setup_site_config()
        self.setup_categories()
        self.collected_urls: set = set()
        self.requests_count = 0
        self.max_requests_before_restart = 100
        self.request_delay = 3.0  # 기본 3초 딜레이
        self.check_robots_txt()
        atexit.register(self.cleanup)

        # 진행 상황 저장 디렉토리
        self.progress_dir = Path('data/progress')
        self.progress_dir.mkdir(parents=True, exist_ok=True)

    def save_progress(self, recipes: List[Dict], category: str) -> None:
        """
        진행 상황 저장
        
        Args:
            recipes: 수집된 레시피 목록
            category: 카테고리명
        """
        # 파일명에서 특수문자 제거
        safe_category = category.replace('/', '_').replace('\\', '_')
        progress_file = self.progress_dir / f"progress_{datetime.now().strftime('%Y%m%d')}_{safe_category}.json"
        
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
            logger.info(f"{category} 카테고리 진행 상황 저장 완료: {len(recipes)}개")
        except Exception as e:
            logger.error(f"진행 상황 저장 중 오류: {str(e)}")

    def load_progress(self, category: str) -> List[Dict]:
        """
        이전 진행 상황 로드
        
        Args:
            category: 카테고리명
            
        Returns:
            이전에 수집된 레시피 목록
        """
        safe_category = category.replace('/', '_').replace('\\', '_')
        progress_file = self.progress_dir / f"progress_{datetime.now().strftime('%Y%m%d')}_{safe_category}.json"
        
        if progress_file.exists():
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"진행 상황 로드 중 오류: {str(e)}")
        return []

    def check_robots_txt(self) -> None:
        """
        robots.txt 확인
        
        크롤링 허용 여부와 딜레이 설정을 확인합니다.
        네이버 API는 체크 생략.
        """
        # 네이버 API 사용 시 생략
        if isinstance(self, NaverRecipeCollector):
            logger.info("네이버 API 사용으로 robots.txt 체크 생략")
            return

        if not hasattr(self, 'base_url'):
            return

        try:
            rp = RobotFileParser()
            rp.set_url(f"{self.base_url}/robots.txt")
            rp.read()

            if not rp.can_fetch("*", self.base_url):
                logger.error(f"robots.txt에서 접근이 제한됨: {self.base_url}")
                raise Exception("robots.txt restriction")

            # Crawl-Delay 설정 확인
            crawl_delay = rp.crawl_delay("*")
            if crawl_delay:
                self.request_delay = max(self.request_delay, crawl_delay)

            logger.info(f"robots.txt 확인 완료. 요청 딜레이: {self.request_delay}초")

        except Exception as e:
            logger.warning(f"robots.txt 확인 중 오류 (계속 진행): {str(e)}")

    @abstractmethod
    def setup_site_config(self) -> None:
        """사이트 기본 설정 (URL, 드라이버 등)"""
        pass

    @abstractmethod
    def setup_categories(self) -> None:
        """카테고리 설정"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """리소스 정리"""
        pass

    @abstractmethod
    def get_recipe_urls_from_category(
        self,
        category: str,
        pages: int = 1
    ) -> List[Dict]:
        """카테고리별 레시피 URL 수집"""
        pass

    @abstractmethod
    def crawl_recipe(
        self,
        url: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """개별 레시피 상세 정보 크롤링"""
        pass

    def collect_recipes(
        self,
        categories: Optional[List[str]] = None,
        include_situations: bool = False,
        pages_per_category: int = 50,
        target_count: Optional[int] = None
    ) -> List[Dict]:
        """
        레시피 수집 메인 로직
        
        Args:
            categories: 수집할 카테고리 목록 (None이면 전체)
            include_situations: 상황별 레시피 포함 여부
            pages_per_category: 카테고리당 페이지 수
            target_count: 목표 수집 개수
            
        Returns:
            수집된 레시피 목록
        """
        if categories is None:
            categories = list(self.categories.keys())

        # 기본 목표 개수 설정
        if target_count is None:
            if isinstance(self, TenThousandRecipeCollector):
                target_count = 6500
            else:
                target_count = 3500

        all_recipes = []
        total_count = 0

        try:
            for category in tqdm(categories, desc="카테고리 처리 중"):
                if total_count >= target_count:
                    logger.info(f"목표 개수 {target_count}개 도달")
                    break

                logger.info(f"\n카테고리 '{category}' 수집 중...")

                # 이전 진행 상황 로드
                previous_recipes = self.load_progress(category)
                if previous_recipes:
                    all_recipes.extend(previous_recipes)
                    total_count += len(previous_recipes)
                    logger.info(f"이전 진행 상황 로드: {len(previous_recipes)}개")
                    continue

                # 새로 수집
                recipes = self.get_recipe_urls_from_category(category, pages_per_category)
                all_recipes.extend(recipes)
                total_count += len(recipes)

                # 진행 상황 저장
                self.save_progress(recipes, category)

                time.sleep(self.request_delay)

            # 상황별 레시피 수집 (옵션)
            if include_situations and hasattr(self, 'situation_urls'):
                for situation in tqdm(self.situation_urls.keys(), desc="상황별 레시피 처리 중"):
                    if total_count >= target_count:
                        break

                    logger.info(f"\n상황 '{situation}' 수집 중...")

                    previous_recipes = self.load_progress(f"situation_{situation}")
                    if previous_recipes:
                        all_recipes.extend(previous_recipes)
                        total_count += len(previous_recipes)
                        continue

                    recipes = self.get_recipe_urls_from_category(situation, pages_per_category)
                    all_recipes.extend(recipes)
                    total_count += len(recipes)

                    self.save_progress(recipes, f"situation_{situation}")
                    time.sleep(self.request_delay)

        except KeyboardInterrupt:
            logger.warning("사용자에 의해 중단됨")
        except Exception as e:
            logger.error(f"레시피 수집 중 오류: {str(e)}")
        finally:
            logger.info(f"총 {len(all_recipes)}개의 레시피 수집됨 (중복 제외)")

        return all_recipes

    def save_recipes(self, recipes: List[Dict], filename: Optional[str] = None) -> None:
        """
        수집된 레시피 정보 저장
        
        Args:
            recipes: 레시피 목록
            filename: 저장 파일명 (None이면 자동 생성)
        """
        if not recipes:
            logger.warning("저장할 레시피가 없습니다.")
            return

        try:
            if filename is None:
                filename = f"recipes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            data_dir = Path('data/raw')
            data_dir.mkdir(parents=True, exist_ok=True)

            filepath = data_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)

            logger.info(f"{len(recipes)}개 레시피를 {filepath}에 저장")

        except Exception as e:
            logger.error(f"레시피 저장 중 오류: {str(e)}")

    def crawl_recipes_batch(
        self,
        recipe_infos: List[Dict],
        output_dir: Path,
        batch_size: int = 100
    ) -> None:
        """
        레시피를 배치 단위로 크롤링
        
        대량 크롤링 시 배치 단위로 저장하여 중간 실패에 대비합니다.
        
        Args:
            recipe_infos: 크롤링할 레시피 정보 목록
            output_dir: 출력 디렉토리
            batch_size: 배치 크기
        """
        total_batches = (len(recipe_infos) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(recipe_infos))
            batch_urls = recipe_infos[start_idx:end_idx]

            logger.info(f"\nProcessing batch {batch_idx + 1}/{total_batches}")

            collected_recipes = []
            for recipe_info in tqdm(batch_urls, desc=f"Batch {batch_idx + 1}"):
                recipe = self.crawl_recipe(recipe_info['url'])
                if recipe:
                    recipe.update({
                        'category': recipe_info.get('category', ''),
                        'view_count': recipe_info.get('view_count', 0)
                    })
                    collected_recipes.append(recipe)

                time.sleep(self.request_delay)

            if collected_recipes:
                batch_file = output_dir / f"recipes_batch_{batch_idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(batch_file, 'w', encoding='utf-8') as f:
                    json.dump(collected_recipes, f, ensure_ascii=False, indent=2)
                logger.info(f"배치 {batch_idx + 1} 저장 완료: {len(collected_recipes)}개")

            time.sleep(self.request_delay)


# ============================================================
# 만개의레시피 수집기
# ============================================================

class TenThousandRecipeCollector(BaseRecipeCollector):
    """
    만개의레시피 전용 수집기
    
    Selenium을 사용한 동적 크롤링으로 레시피 데이터를 수집합니다.
    
    Target:
        - URL: https://www.10000recipe.com
        - 목표 수집량: 6,500+ 레시피
        
    Features:
        - 카테고리별 수집
        - 상황별 수집 (예: 다이어트, 야식)
        - 조회수 기반 정렬
    """

    def setup_site_config(self) -> None:
        """사이트 기본 설정"""
        self.base_url = "https://www.10000recipe.com"
        self.driver = None
        
        if SELENIUM_AVAILABLE:
            self.setup_driver()
        else:
            logger.warning("Selenium이 설치되지 않음. 일부 기능 제한됨.")

    def setup_driver(self) -> None:
        """Selenium WebDriver 설정"""
        if not SELENIUM_AVAILABLE:
            return

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            logger.info("Chrome WebDriver 초기화 완료")
        except WebDriverException as e:
            logger.error(f"WebDriver 초기화 실패: {str(e)}")
            self.driver = None

    def setup_categories(self) -> None:
        """카테고리 설정"""
        self.categories = {}
        for category_key, category_data in UNIFIED_CATEGORIES.items():
            category_name = category_data['name']
            self.categories[category_name] = category_data['tenthousand_query']

        # 상황별 URL
        self.situation_urls = {
            "다이어트": "diet",
            "야식": "night",
            "간식": "snack",
            "손님접대": "guest",
            "술안주": "drink"
        }

    def cleanup(self) -> None:
        """리소스 정리"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver 종료 완료")
            except Exception as e:
                logger.warning(f"WebDriver 종료 중 오류: {str(e)}")

    def get_recipe_urls_from_category(
        self,
        category: str,
        pages: int = 1
    ) -> List[Dict]:
        """
        카테고리별 레시피 URL 수집
        
        Args:
            category: 카테고리명
            pages: 수집할 페이지 수
            
        Returns:
            레시피 정보 목록 (url, category, source)
        """
        if not self.driver:
            logger.error("WebDriver가 초기화되지 않음")
            return []

        recipes = []
        queries = self.categories.get(category, [category])

        for query in queries:
            for page in range(1, pages + 1):
                try:
                    url = f"{self.base_url}/recipe/list.html?q={query}&order=reco&page={page}"
                    self.driver.get(url)
                    time.sleep(2)

                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    recipe_items = soup.select('.common_sp_list_ul li')

                    for item in recipe_items:
                        link = item.select_one('a')
                        if link:
                            href = link.get('href', '')
                            if href:
                                recipe_url = self.base_url + href if href.startswith('/') else href
                                if recipe_url not in self.collected_urls:
                                    self.collected_urls.add(recipe_url)
                                    recipes.append({
                                        'url': recipe_url,
                                        'category': category,
                                        'source': '만개의레시피'
                                    })

                    self.requests_count += 1
                    time.sleep(self.request_delay)

                except TimeoutException:
                    logger.warning(f"페이지 로드 타임아웃: {url}")
                except Exception as e:
                    logger.error(f"URL 수집 중 오류: {str(e)}")
                    continue

        logger.info(f"'{category}' 카테고리에서 {len(recipes)}개 URL 수집")
        return recipes

    def crawl_recipe(
        self,
        url: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        개별 레시피 크롤링
        
        Args:
            url: 레시피 URL
            max_retries: 최대 재시도 횟수
            
        Returns:
            레시피 데이터 딕셔너리 또는 None
        """
        if not self.driver:
            return None

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                time.sleep(2)

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')

                # 제목
                title_elem = soup.select_one('.view2_summary h3')
                title = title_elem.text.strip() if title_elem else ""

                # 재료
                ingredients = []
                for ing in soup.select('.ready_ingre3 ul li'):
                    ing_text = ing.text.strip()
                    if ing_text:
                        ingredients.append(ing_text)

                # 조리 단계
                steps = []
                for step in soup.select('.view_step_cont'):
                    step_text = step.text.strip()
                    if step_text:
                        steps.append(step_text)

                # 조회수
                view_elem = soup.select_one('.hit')
                view_count = 0
                if view_elem:
                    try:
                        view_text = view_elem.text.replace(',', '').strip()
                        view_count = int(''.join(filter(str.isdigit, view_text)))
                    except ValueError:
                        pass

                if title:  # 최소한 제목은 있어야 함
                    return {
                        'url': url,
                        'title': title,
                        'ingredients': ingredients,
                        'steps': steps,
                        'view_count': view_count,
                        'source': '만개의레시피',
                        'crawled_at': datetime.now().isoformat()
                    }

            except TimeoutException:
                logger.warning(f"크롤링 타임아웃 (시도 {attempt + 1}/{max_retries}): {url}")
            except Exception as e:
                logger.warning(f"크롤링 재시도 {attempt + 1}/{max_retries}: {str(e)}")

            time.sleep(2)

        logger.error(f"크롤링 실패: {url}")
        return None


# ============================================================
# 네이버 요리백과 수집기
# ============================================================

class NaverRecipeCollector(BaseRecipeCollector):
    """
    네이버 요리백과 전용 수집기
    
    네이버 지식백과의 요리백과 섹션에서 구조화된 레시피 데이터를 수집합니다.
    Selenium 없이 requests만으로 동작합니다.
    
    Target:
        - URL: https://terms.naver.com (요리백과 섹션)
        - 목표 수집량: 1,000+ 레시피
        
    Features:
        - 정제된 레시피 데이터
        - 전문적인 조리 정보
        - 영양 정보 포함
    """

    def setup_site_config(self) -> None:
        """사이트 기본 설정"""
        load_dotenv()
        self.base_url = "https://terms.naver.com"
        self.list_url = "https://terms.naver.com/list.naver"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def setup_categories(self) -> None:
        """카테고리 설정"""
        self.categories = {}
        for category_key, category_data in UNIFIED_CATEGORIES.items():
            category_name = category_data['name']
            self.categories[category_name] = category_data['naver_ids']

    def cleanup(self) -> None:
        """리소스 정리"""
        if hasattr(self, 'session') and self.session:
            self.session.close()

    def get_recipe_urls_from_category(
        self,
        category: str,
        pages: int = 1
    ) -> List[Dict]:
        """
        카테고리별 레시피 URL 수집
        
        Args:
            category: 카테고리명
            pages: 수집할 페이지 수
            
        Returns:
            레시피 정보 목록
        """
        recipes = []
        category_ids = self.categories.get(category, [])

        for cat_id in category_ids:
            for page in range(1, pages + 1):
                try:
                    params = {
                        'cid': '48180',  # 요리백과 CID
                        'categoryId': cat_id,
                        'page': page
                    }

                    response = self.session.get(
                        self.list_url,
                        params=params,
                        timeout=10
                    )

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        for item in soup.select('.content_list li'):
                            link = item.select_one('a')
                            if link:
                                href = link.get('href', '')
                                if href:
                                    recipe_url = self.base_url + href if href.startswith('/') else href
                                    if recipe_url not in self.collected_urls:
                                        self.collected_urls.add(recipe_url)
                                        recipes.append({
                                            'url': recipe_url,
                                            'category': category,
                                            'source': '네이버요리백과',
                                            'category_id': cat_id
                                        })

                    self.requests_count += 1
                    time.sleep(self.request_delay)

                except requests.RequestException as e:
                    logger.error(f"URL 수집 중 오류: {str(e)}")
                    continue

        logger.info(f"'{category}' 카테고리에서 {len(recipes)}개 URL 수집")
        return recipes

    def crawl_recipe(
        self,
        url: str,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """
        개별 레시피 크롤링
        
        Args:
            url: 레시피 URL
            max_retries: 최대 재시도 횟수
            
        Returns:
            레시피 데이터 딕셔너리 또는 None
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 제목
                    title_elem = soup.select_one('.headword')
                    title = title_elem.text.strip() if title_elem else ""

                    # 설명
                    desc_elem = soup.select_one('.size_ct_v2')
                    description = desc_elem.text.strip() if desc_elem else ""

                    # 재료
                    ingredients = []
                    for ing in soup.select('.ingredient_list li, .txt_indent'):
                        ing_text = ing.text.strip()
                        if ing_text:
                            ingredients.append(ing_text)

                    # 조리 단계
                    steps = []
                    for step in soup.select('.step_list li, .txt_indent'):
                        step_text = step.text.strip()
                        if step_text and step_text not in ingredients:
                            steps.append(step_text)

                    if title:
                        return {
                            'url': url,
                            'title': title,
                            'description': description,
                            'ingredients': ingredients,
                            'steps': steps,
                            'source': '네이버요리백과',
                            'crawled_at': datetime.now().isoformat()
                        }

            except requests.RequestException as e:
                logger.warning(f"크롤링 재시도 {attempt + 1}/{max_retries}: {str(e)}")

            time.sleep(2)

        logger.error(f"크롤링 실패: {url}")
        return None


# ============================================================
# 유틸리티 함수
# ============================================================

def get_category_id_from_url(url: str) -> Optional[str]:
    """URL에서 안전하게 categoryId 추출"""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get('categoryId', [None])[0]
    except Exception:
        return None