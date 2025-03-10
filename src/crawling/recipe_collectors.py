from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import time
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm
import logging
import atexit
from abc import ABC, abstractmethod
import requests
from urllib.robotparser import RobotFileParser
import os
from dotenv import load_dotenv
import random
from urllib.parse import parse_qs, urlparse

from .parsers.recipe_parsers import TenThousandRecipeParser, NaverRecipeParser, create_parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_category_id_from_url(url: str) -> Optional[str]:
    """URL에서 안전하게 categoryId 추출"""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get('categoryId', [None])[0]
    except Exception:
        return None

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
        "categories": [
            "커피", "차/다류", "주스", "건강음료", "스무디/쉐이크",
            "와인/포도주", "칵테일", "맥주", "소주", "탁주/동동주/전통주",
            "기타주류", "빙수", "아이스크림"
        ],
        "naver_ids": [
            "48227", "48228", "48392", "48393", "48394", "48395", "48396",
            "48397", "48398", "48399", "48400", "48401", "48402"
        ],
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

def map_category_name(category_id: str = None, site_query: str = None) -> str:
    """카테고리 ID나 쿼리를 통합 카테고리명으로 변환"""
    if category_id:
        for category_data in UNIFIED_CATEGORIES.values():
            if category_id in category_data["naver_ids"]:
                return category_data["name"]
    elif site_query:
        for category_data in UNIFIED_CATEGORIES.values():
            if site_query in category_data["tenthousand_query"]:  # == 를 in으로 수정
                return category_data["name"]
    return UNIFIED_CATEGORIES["OTHERS"]["name"]

# 그 다음 BaseRecipeCollector 클래스...

class BaseRecipeCollector(ABC):
    """레시피 수집 베이스 클래스"""
    
    def __init__(self):
        self.setup_site_config()
        self.setup_categories()
        self.collected_urls = set()
        self.requests_count = 0
        self.max_requests_before_restart = 100
        self.request_delay = 3  # 5초 딜레이
        self.check_robots_txt()  # robots.txt 확인
        atexit.register(self.cleanup)

        self.progress_dir = Path('data/progress')
        self.progress_dir.mkdir(parents=True, exist_ok=True)

    def save_progress(self, recipes: List[Dict], category: str):
        """진행 상황 저장"""
        # 파일명에서 특수문자 제거
        safe_category = category.replace('/', '_').replace('\\', '_')
        progress_file = self.progress_dir / f"progress_{datetime.now().strftime('%Y%m%d')}_{safe_category}.json"
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
            logger.info(f"{category} 카테고리 진행 상황 저장 완료: {len(recipes)}개")
        except Exception as e:
            logger.error(f"진행 상황 저장 중 오류 발생: {str(e)}")

    def load_progress(self, category: str) -> List[Dict]:
        """이전 진행 상황 로드"""
        progress_file = f"progress_{datetime.now().strftime('%Y%m%d')}_{category}.json"
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def check_robots_txt(self):
        """robots.txt 확인"""
        # 네이버는 API를 사용하므로 robots.txt 체크 스킵
        if isinstance(self, NaverRecipeCollector):
            logger.info("네이버 API 사용으로 robots.txt 체크 생략")
            return


        try:
            rp = RobotFileParser()
            rp.set_url(f"{self.base_url}/robots.txt")
            rp.read()
            user_agent = "*"
            
            if not rp.can_fetch(user_agent, self.base_url):
                logger.error(f"robots.txt에서 접근이 제한됨: {self.base_url}")
                raise Exception("robots.txt restriction")
            
            self.crawl_delay = rp.crawl_delay(user_agent)
            if self.crawl_delay:
                self.request_delay = max(self.request_delay, self.crawl_delay)
            
            logger.info(f"robots.txt 확인 완료. 요청 딜레이: {self.request_delay}초")
            
        except Exception as e:
            logger.error(f"robots.txt 확인 중 오류: {str(e)}")
            raise
        
    @abstractmethod
    def setup_site_config(self):
        """사이트 기본 설정 (URL 등)"""
        pass
        
    @abstractmethod
    def setup_categories(self):
        """카테고리 설정"""
        pass

    @abstractmethod
    def cleanup(self):
        """리소스 정리"""
        pass

    @abstractmethod
    def get_recipe_urls_from_category(self, category: str, pages: int = 1) -> List[Dict]:
        """카테고리별 레시피 URL 수집"""
        pass

    @abstractmethod
    def crawl_recipe(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """개별 레시피 상세 정보 크롤링"""
        pass

    def collect_recipes(self, categories: List[str] = None, include_situations: bool = False, pages_per_category: int = 50):
        """레시피 수집 공통 로직"""
        if categories is None:
            categories = list(self.categories.keys())
            
        all_recipes = []
        total_count = 0
        target_count = 6500 if isinstance(self, TenThousandRecipeCollector) else 3500
        
        try:
            # 기본 카테고리 수집
            for category in tqdm(categories, desc="카테고리 처리 중"):
                if total_count >= target_count:
                    break

                logger.info(f"\n카테고리 '{category}' 수집 중...")

                # 이전 진행 상황 로드
                previous_recipes = self.load_progress(category)
                if previous_recipes:
                    all_recipes.extend(previous_recipes)
                    total_count += len(previous_recipes)
                    continue

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

                    # 이전 진행 상황 로드
                    previous_recipes = self.load_progress(f"situation_{situation}")
                    if previous_recipes:
                        all_recipes.extend(previous_recipes)
                        total_count += len(previous_recipes)
                        continue

                    recipes = self.get_recipe_urls_from_category(situation, pages_per_category)
                    all_recipes.extend(recipes)
                    total_count += len(recipes)

                    # 진행 상황 저장
                    self.save_progress(recipes, f"situation_{situation}")

                    time.sleep(self.request_delay)
                    
        except Exception as e:
            logger.error(f"레시피 수집 중 오류 발생: {str(e)}")
        finally:
            logger.info(f"총 {len(all_recipes)}개의 레시피 수집됨 (중복 제외)")
            
        return all_recipes

    def save_recipes(self, recipes: List[Dict], filename: str = None):
        """수집된 레시피 정보 저장"""
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
            logger.error(f"레시피 저장 중 오류 발생: {str(e)}")

    def crawl_recipes_batch(self, recipe_infos: list, output_dir: Path, batch_size: int = 100):
        """레시피를 배치 단위로 크롤링"""
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
                        'category': recipe_info['category'],
                        'view_count': recipe_info.get('view_count', 0)
                    })
                    collected_recipes.append(recipe)
                    
                time.sleep(self.request_delay)
            
            if collected_recipes:
                batch_file = output_dir / f"recipes_batch_{batch_idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(batch_file, 'w', encoding='utf-8') as f:
                    json.dump(collected_recipes, f, ensure_ascii=False, indent=2)
                
            time.sleep(self.request_delay)

class TenThousandRecipeCollector(BaseRecipeCollector):
    """만개의레시피 전용 수집기"""
    
    def setup_site_config(self):
        """사이트 기본 설정"""
        self.base_url = "https://www.10000recipe.com"
        self.setup_driver()
        self.parser = TenThousandRecipeParser()

    def setup_categories(self):
        """카테고리 설정"""
        self.categories = {}
        for category_key, category_data in UNIFIED_CATEGORIES.items():
            category_name = category_data['name']
            self.categories[category_name] = category_data['tenthousand_query']
                    
        self.situation_urls = {
            "손님접대": "/recipe/list.html?q=손님접대",
            "술안주": "/recipe/list.html?q=술안주",
            "다이어트": "/recipe/list.html?q=다이어트",
            "간식": "/recipe/list.html?q=간식",
            "야식": "/recipe/list.html?q=야식",
            "주말": "/recipe/list.html?q=주말요리",
            "초스피드": "/recipe/list.html?q=초스피드",
            "편의점음식": "/recipe/list.html?q=편의점",
            "도시락": "/recipe/list.html?q=도시락",
            "영양식": "/recipe/list.html?q=영양식"
        }

    def setup_driver(self):
        """Selenium 드라이버 설정"""
        try:
            logger.info("Chrome options 설정 중...")
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # 페이지 로드 전략 추가
            chrome_options.page_load_strategy = 'eager'
            
            self.driver = webdriver.Chrome(options=chrome_options)
            # timeout 설정 변경
            self.driver.set_page_load_timeout(60)  # 60초로 증가
            self.driver.set_script_timeout(60)    # 스크립트 타임아웃도 설정
            self.driver.implicitly_wait(20)       # implicit wait도 증가
            
            logger.info("Chrome WebDriver 시작 완료")
            
        except Exception as e:
            logger.error(f"Chrome WebDriver 설정 오류: {str(e)}")
            raise

    def cleanup(self):
        """드라이버 정리"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                logger.info("WebDriver 정리 완료")
        except Exception as e:
            logger.error(f"WebDriver 정리 중 오류 발생: {str(e)}")

    def restart_driver(self):
        """드라이버 재시작"""
        self.cleanup()
        time.sleep(2)
        self.setup_driver()
    
    def get_recipe_urls_from_category(self, category: str, pages: int = 1) -> List[Dict]:
        """카테고리별 레시피 URL 수집"""
        recipe_infos = []
        queries = self.categories.get(category)
        
        if not queries:
            logger.error(f"Unknown category: {category}")
            return recipe_infos
            
        for query in queries:
            for page in range(1, pages + 1):
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        url = f"{self.base_url}/recipe/list.html?q={query}&order=accuracy&page={page}"
                        logger.info(f"URL 접근: {url}")
                        
                        self.driver.get(url)
                        time.sleep(self.request_delay)
                        
                        recipe_cards = self.driver.find_elements(By.CSS_SELECTOR, "li.common_sp_list_li")
                        
                        # 조회수가 높은 레시피 우선 수집
                        recipes_with_views = []
                        for card in recipe_cards:
                            try:
                                link_el = card.find_element(By.CSS_SELECTOR, "div.common_sp_thumb a")
                                title_el = card.find_element(By.CSS_SELECTOR, "div.common_sp_caption_tit")
                                # 조회수 요소 찾기 (있는 경우)
                                try:
                                    views_el = card.find_element(By.CSS_SELECTOR, "div.common_sp_caption_rv")
                                    views = int(views_el.text.strip().replace(",", ""))
                                except:
                                    views = 0
                                    
                                url = link_el.get_attribute('href')
                                if url in self.collected_urls:
                                    continue
                                    
                                recipes_with_views.append({
                                    'url': url,
                                    'title': title_el.text.strip(),
                                    'category': category,
                                    'views': views
                                })
                                
                            except Exception as e:
                                logger.error(f"레시피 카드 처리 중 오류: {str(e)}")
                                continue
                        
                        # 조회수 기준으로 정렬
                        recipes_with_views.sort(key=lambda x: x['views'], reverse=True)
                        
                        # 상위 레시피만 선택
                        for recipe in recipes_with_views[:20]:  # 페이지당 상위 10개
                            self.collected_urls.add(recipe['url'])
                            recipe_infos.append({
                                'url': recipe['url'],
                                'title': recipe['title'],
                                'category': category,
                                'view_count': recipe['views'],
                                'collected_at': datetime.now().isoformat(),
                                'source': '만개의레시피'
                            })
                        
                        time.sleep(self.request_delay)
                        break
                        
                    except WebDriverException:
                        logger.warning(f"WebDriver 오류 발생, 재시도 {retry_count + 1}/{max_retries}")
                        self.restart_driver()
                        retry_count += 1
                        time.sleep(self.request_delay)
                    
        return recipe_infos

    def crawl_recipe(self, url: str, max_retries: int = 3) -> Optional[Dict]:
        """개별 레시피 상세 정보 크롤링"""
        for attempt in range(max_retries):
            try:
                if self.requests_count >= self.max_requests_before_restart:
                    self.restart_driver()
                    self.requests_count = 0
                
                self.requests_count += 1
                logger.info(f"레시피 크롤링 중: {url}")
                self.driver.get(url)
                time.sleep(self.request_delay)
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # 재료 먼저 체크
                ingredients = self.parser.parse_ingredients(soup)
                if ingredients is None:  # 재료가 없으면 건너뛰기
                    logger.info(f"재료 없음, 레시피 건너뛰기: {url}")
                    return None
                
                recipe = {
                    'url': url,
                    'title': self.parser.parse_title(soup),
                    'ingredients': ingredients,  # 이미 파싱된 재료 사용
                    'steps': self.parser.parse_steps(soup),
                    'metadata': self.parser.parse_metadata(soup),
                    'crawled_at': datetime.now().isoformat()
                }
                
                return recipe
                
            except Exception as e:
                logger.error(f"시도 {attempt + 1} 실패: {str(e)}")
                if attempt == max_retries - 1:
                    return None
                
                self.restart_driver()
                time.sleep(self.request_delay)

class NaverRecipeCollector(BaseRecipeCollector):
    """네이버 검색 API 기반 레시피 수집기"""
    
    def setup_site_config(self):
        """사이트 기본 설정"""
        self.base_url = "https://terms.naver.com"
        load_dotenv()
        self.client_id = os.getenv('NAVER_CLIENT_ID')
        self.client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("네이버 API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")
            
        self.parser = NaverRecipeParser()
    
    def setup_categories(self):
        """카테고리 설정"""
        self.categories = {}
        for category_key, category_data in UNIFIED_CATEGORIES.items():
            self.categories[category_data["name"]] = ", ".join(category_data["naver_ids"])


    def cleanup(self):
        """리소스 정리 - API 기반이라 특별한 정리가 필요없음"""
        pass
    

    def get_recipe_urls_from_category(self, category: str, pages: int = 1) -> List[Dict]:
        """카테고리별 레시피 URL 수집"""
        recipe_infos = []
        try:
            category_ids = self.categories.get(category)
            if not category_ids:
                logger.error(f"Unknown category: {category}")
                return recipe_infos
            
            # 카테고리 ID 리스트로 변환
            category_ids = [id.strip() for id in category_ids.split(',')]
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })

            for category_id in category_ids:
                for page in range(1, pages + 1):
                    try:
                        url = f"https://terms.naver.com/list.naver?categoryId={category_id}&page={page}"
                        logger.info(f"Fetching URL: {url}")
                        
                        response = session.get(url, timeout=10)
                        response.raise_for_status()
                        
                    except requests.exceptions.Timeout:
                        logger.error(f"Request timeout for {url}")
                        continue
                    except requests.exceptions.HTTPError as e:
                        logger.error(f"HTTP error occurred: {e}")
                        if response.status_code == 404:
                            break  # 페이지가 없으면 다음 카테고리로
                        continue
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Request failed: {e}")
                        continue
                    
                    try:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        recipe_items = soup.select('ul.content_list > li')
                        
                        if not recipe_items:
                            logger.info(f"No more recipes found in category {category} (ID: {category_id}) after page {page}")
                            break
                            
                        for item in recipe_items:
                            try:
                                # URL과 제목 추출
                                link_el = item.select_one('div.info_area > div.subject > strong.title > a')
                                if not link_el:
                                    continue
                                    
                                recipe_url = f"https://terms.naver.com{link_el['href']}"
                                if recipe_url in self.collected_urls:
                                    continue
                                    
                                title = link_el.get_text(strip=True)
                                description_el = item.select_one('p.desc')
                                description = description_el.get_text(strip=True) if description_el else ""
                                
                                # 일반적인 요리 관련 키워드 체크
                                if not any(keyword in description or keyword in title 
                                        for keyword in ['만드는', '레시피', '요리', '만들기']):
                                    continue
                                    
                                recipe_info = {
                                    'url': recipe_url,
                                    'title': title,
                                    'category': category,
                                    'description': description,
                                    'collected_at': datetime.now().isoformat(),
                                    'source': '네이버 요리백과'
                                }
                                
                                recipe_infos.append(recipe_info)
                                self.collected_urls.add(recipe_url)
                                logger.info(f"Collected recipe: {title}")
                                
                            except Exception as e:
                                logger.error(f"Error processing recipe item: {str(e)}")
                                continue
                        
                        time.sleep(self.request_delay)
                        
                    except Exception as e:
                        logger.error(f"Error processing page content: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Fatal error in get_recipe_urls_from_category: {e}", exc_info=True)
        
        logger.info(f"카테고리 '{category}'에서 {len(recipe_infos)}개의 레시피 URL 수집됨")
        return recipe_infos

    def crawl_recipe(self, url: str, category: str = None, max_retries: int = 3) -> Optional[Dict]:
        """개별 레시피 상세 정보 크롤링"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        for attempt in range(max_retries):
            try:
                logger.info(f"레시피 크롤링 시도 {attempt + 1}/{max_retries}: {url}")
                
                # URL 유효성 검사
                if not url or not url.startswith('http'):
                    logger.error(f"유효하지 않은 URL: {url}")
                    return None
                
                # 요청 전 딜레이
                time.sleep(self.request_delay)
                response = session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 기본 정보 파싱
                title = self.parser.parse_title(soup)
                if not title:
                    logger.warning("제목을 찾을 수 없음")
                    continue

                # 각 섹션별 파싱 시도 (예외 처리 포함)
                try:
                    ingredients = self.parser.parse_ingredients(soup)
                except Exception as e:
                    logger.error(f"재료 파싱 중 오류: {str(e)}")
                    ingredients = []

                try:
                    steps = self.parser.parse_steps(soup)
                except Exception as e:
                    logger.error(f"조리 단계 파싱 중 오류: {str(e)}")
                    steps = []

                try:
                    metadata = self.parser.parse_metadata(soup)
                except Exception as e:
                    logger.error(f"메타데이터 파싱 중 오류: {str(e)}")
                    metadata = {}
                recipe = {
                    'url': url,
                    'id': url.split('docId=')[1].split('&')[0] if 'docId=' in url else '',
                    'title': title,
                    'category': category or '기타',
                    'situation': [],
                    'ingredients': ingredients or [],  # None 방지
                    'steps': steps or [],  # None 방지
                    'metadata': metadata or {},  # None 방지
                    'crawled_at': datetime.now().isoformat()
                }

                # 카테고리 ID 매핑
                category_id = get_category_id_from_url(url)
                if category_id and not category:
                    recipe['category'] = map_category_name(category_id=category_id)

                logger.info(f"레시피 크롤링 성공: {title}")
                return recipe

            except requests.exceptions.RequestException as e:
                logger.error(f"요청 실패: {str(e)} (시도 {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.error(f"예상치 못한 오류: {str(e)} (시도 {attempt + 1}/{max_retries})")
                logger.error(traceback.format_exc())

            if attempt < max_retries - 1:
                time.sleep(self.request_delay * 2)  # 재시도 전 더 긴 대기
                continue
            
        logger.error(f"최대 재시도 횟수 초과: {url}")
        return None
 
    def crawl_recipes_batch(self, recipe_infos: list, output_dir: Path, batch_size: int = 100):
        """레시피를 배치 단위로 크롤링"""
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
                        'category': recipe_info['category'],
                        'description': recipe_info.get('description', '')
                    })
                    collected_recipes.append(recipe)
                    
                time.sleep(self.request_delay)
            
            if collected_recipes:
                batch_file = output_dir / f"naver_recipes_batch_{batch_idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(batch_file, 'w', encoding='utf-8') as f:
                    json.dump(collected_recipes, f, ensure_ascii=False, indent=2)
                
            time.sleep(self.request_delay)
    