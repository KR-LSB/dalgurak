from abc import ABC, abstractmethod
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Dict, List, Optional, Union, Any
import html
import json
from pathlib import Path
import traceback
import re
from typing import Dict, List, Optional, Any
from src.preprocessing.recipe_patterns import RecipePatternDB
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseRecipeParser(ABC):
    """레시피 파서 기본 클래스"""
    
    def __init__(self):
        self.pattern_db = RecipePatternDB()
    
    def get_patterns(self, domain: str) -> Optional[Dict]:
        """현재 사이트에 대한 패턴 가져오기"""
        return self.pattern_db.get_pattern(domain)
    
    def parse_with_pattern(self, soup: BeautifulSoup, pattern: Dict, selector: str, attribute: str = 'text') -> str:
        """패턴을 사용한 파싱"""
        if isinstance(selector, list):
            # 여러 선택자 시도
            for sel in selector:
                element = soup.select_one(sel)
                if element:
                    break
        else:
            element = soup.select_one(selector)
            
        if element:
            return getattr(element, attribute, '').strip()
        return ''
        
    @abstractmethod
    def parse_title(self, soup: BeautifulSoup) -> str:
        """레시피 제목 파싱"""
        pass
    @abstractmethod
    def parse_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """메타데이터(조리시간, 난이도, 분량 등) 파싱"""
        pass    

    @abstractmethod
    def parse_ingredients(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """재료 정보 파싱"""
        pass
        
    @abstractmethod
    def parse_steps(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """조리 단계 파싱"""
        pass

    def clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        return " ".join(text.strip().split())
        
    def normalize_amount(self, amount: str) -> Dict[str, Optional[float]]:
        if not amount:
            return {'original': '', 'value': None, 'unit': None}
            
        result = {'original': amount, 'value': None, 'unit': None}
        
        # 분수 처리
        fraction_pattern = r'(\d+)?\s*(?:과\s*)?(\d+)/(\d+)'
        fraction_match = re.search(fraction_pattern, amount)
        if fraction_match:
            whole = int(fraction_match.group(1)) if fraction_match.group(1) else 0
            num = int(fraction_match.group(2))
            denom = int(fraction_match.group(3))
            result['value'] = whole + (num / denom)
        else:
            # 일반 숫자 처리
            numbers = re.findall(r'\d+(?:\.\d+)?', amount)
            if numbers:
                result['value'] = float(numbers[0])
        
        # 확장된 단위 목록
        units = {
            '중량': ['g', 'kg', '근', 'mg'],
            '부피': ['ml', 'l', '컵', '종이컵', '밥숟가락', '스푼', '큰술', '작은술'],
            '개수': ['개', '알', '조각', '장', '포기' '마리', '톨', '통', '묶음', '봉지', '봉', '팩', '캔'],
            '기타': ['꼬집', '줌', '약간', '적당량', '주먹', '다시', '움큼']
        }
        
        for category in units.values():
            for unit in category:
                if unit in amount:
                    result['unit'] = unit
                    break
            if result['unit']:
                break
        
        return result

    def normalize_time(self, time_str: str) -> Dict[str, Optional[int]]:
        """조리시간 정규화"""
        result = {'original': time_str, 'minutes': None}
        
        if not time_str:
            return result
            
        try:
            cleaned = time_str.replace(' ', '')
            if '시간' in cleaned:
                hours = int(cleaned.split('시간')[0])
                minutes = hours * 60
                remaining = cleaned.split('시간')[1]
                if '분' in remaining:
                    minutes += int(remaining.split('분')[0])
            elif '분' in cleaned:
                minutes = int(cleaned.split('분')[0])
            else:
                return result
                
            result['minutes'] = minutes
            
        except Exception:
            pass
            
        return result

    def normalize_difficulty(self, difficulty: str) -> Dict[str, Optional[int]]:
        """난이도 정규화"""
        result = {'original': difficulty, 'level': None}
        
        if not difficulty:
            return result
            
        difficulty_map = {
            '아무나': 1,
            '초급': 1,
            '중급': 2,
            '고급': 3,
            '요리사': 3
        }
        
        cleaned = difficulty.replace(' ', '')
        for key, value in difficulty_map.items():
            if key in cleaned:
                result['level'] = value
                break
                
        return result
    
def create_parser(site_type: str) -> BaseRecipeParser:
    """파서 팩토리 함수"""
    parsers = {
        'naver': NaverRecipeParser,
        '10000recipe': TenThousandRecipeParser
    }
    
    parser_class = parsers.get(site_type)
    if not parser_class:
        raise ValueError(f"지원하지 않는 사이트 타입입니다: {site_type}")
        
    return parser_class()

class TenThousandRecipeParser(BaseRecipeParser):
    """만개의레시피 전용 파서"""
    
    # 유효한 단위 목록
    VALID_UNITS = [
        # 중량 단위
        'g', 'kg', 'mg', '근', '근량', '근치', '되',
        # 부피 단위
        'ml', 'l', '컵', '종이컵', 
        '밥숟가락', '스푼', '큰술', '작은술', '티스푼',
        # 개수 단위
        '개', '알', '조각', '장', '포기', '마리', '톨', 
        '통', '묶음', '봉지', '봉', '팩', '캔',
        # 길이/넓이 단위
        'cm', 'm', '치', '인치',
        # 기타 단위
        '꼬집', '줌', '주먹', '다시', '움큼',
        '한번', '적당량', '약간', '조금'
    ]
    
    # 모음집/리스트성 글 키워드
    COLLECTION_KEYWORDS = [
        'best', 'top', 'pick', '추천', '모음', 
        '레시피모음', '총정리', '정리', '특집',
        '리스트', '종류', '목록', '총집합'
    ]

    def __init__(self):
        super().__init__()
        self.patterns = self.get_patterns('10000recipe.com')

    def parse_title(self, soup: BeautifulSoup) -> str:
        """레시피 제목 파싱"""
        # 여러 선택자 시도
        selectors = [
            "h3.view2_summary > strong",
            "div.view2_summary h3",
            "div.view_title",
            "div.view_recipe_title",
            "div.view_ready_title", 
            "meta[property='og:title']"
        ]
        
        for selector in selectors:
            title_element = soup.select_one(selector)
            if title_element:
                if selector.startswith('meta'):
                    title = title_element.get('content', '')
                else:
                    title = title_element.text
                    
                title = self.clean_text(title)
                if title:
                    return title
        
        # 마지막 시도: 페이지 제목
        if soup.title:
            title = soup.title.text
            if '만개의레시피' in title:
                title = title.replace('만개의레시피', '').strip()
            if '|' in title:
                title = title.split('|')[0].strip()
            return title
                
        return ""

    def parse_ingredients(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """재료 정보 파싱"""
        ingredients = []
        try:
            # 재료가 있는지 먼저 체크
            ingre_div = soup.find('div', {'id': 'divConfirmedMaterialArea'})
            if not ingre_div:
                ingre_div = soup.find('div', class_='ready_ingre3')
            
            # 재료 섹션이 없으면 None 반환
            if not ingre_div or not ingre_div.find_all('li'):
                logger.info("재료 정보가 없는 페이지 건너뛰기")
                return None
            
            # 모음집/리스트성 글 체크
            title = self.parse_title(soup)
            description = ''
            meta = soup.find('meta', {'name': 'description'})
            if meta:
                description = meta.get('content', '')
                
            if self._is_collection_post(title, description):
                logger.info(f"모음집/리스트성 글 건너뛰기: {title}")
                return None
                
            # 1. HTML 구조에서 재료 파싱 시도
            ingredients.extend(self._parse_ingredients_from_html(soup))
            
            # 2. 실패시 description에서 파싱
            if not ingredients:
                ingredients.extend(self._parse_ingredients_from_text(description))
                
            # 3. 여전히 재료가 없으면 None 반환
            if not ingredients:
                logger.info("재료 파싱 실패, 페이지 건너뛰기")
                return None
                
            logger.info(f"전체 재료 수: {len(ingredients)}")
            if ingredients:
                logger.info(f"첫 번째 재료: {ingredients[0]}")
                
        except Exception as e:
            logger.error(f"재료 파싱 중 오류 발생: {str(e)}")
            return None  # 예외 발생 시에도 None 반환
            
        return ingredients
        
    def clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
            
        try:
            # 1. 기본 공백 제거
            text = text.strip()
            
            # 2. 연속된 공백을 하나로
            text = re.sub(r'\s+', ' ', text)
            
            # 3. 선택 표현 정리 ('또는', 'or', '/', '혹은' 등)
            text = re.sub(r'\s*(?:또는|or|\/|혹은)\s*', ' 또는 ', text)
            
            # 4. 괄호 안 텍스트 처리
            # (숫자+단위)는 보존, (설명)은 제거
            def clean_parentheses(match):
                content = match.group(1)
                # 숫자+단위 패턴 체크
                if re.search(r'\d+\s*(?:g|kg|ml|개|인분|cm|mm)', content):
                    return f"({content})"
                return ""
            text = re.sub(r'\(([^)]+)\)', clean_parentheses, text)
            
            # 5. 불필요한 문자 제거
            text = text.replace('♡', '').replace('♥', '').replace('★', '')
            text = text.replace('▶', '').replace('▷', '').replace('□', '')
            
            # 6. 특수문자 처리
            text = re.sub(r'[^\w\s가-힣()]+', ' ', text)
            
            # 7. 남은 공백 정리
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            logger.error(f"텍스트 정제 중 오류 발생: {str(e)}, 원본 텍스트: {text}")
            return text.strip()

    def _parse_ingredients_from_html(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """HTML 구조에서 재료 정보 파싱"""
        ingredients = []
        
        ingre_div = soup.find('div', {'id': 'divConfirmedMaterialArea'})
        if not ingre_div:
            ingre_div = soup.find('div', class_='ready_ingre3')
        
        if ingre_div:
            current_group = "주재료"
            
            for element in ingre_div.find_all(['b', 'ul']):
                if element.name == 'b' and 'ready_ingre3_tt' in element.get('class', []):
                    group_text = self.clean_text(element.text.strip('[]'))
                    if group_text and len(group_text) < 20:
                        current_group = group_text
                elif element.name == 'ul':
                    for item in element.find_all('li'):
                        try:
                            # 재료명
                            name_div = item.find('div', class_='ingre_list_name')
                            if not name_div:
                                continue

                            # a 태그에서 재료명 추출
                            name_a = name_div.find('a')
                            if name_a:
                                name = self.clean_text(name_a.text)
                            else:
                                name = self.clean_text(name_div.text)

                            # 수량
                            amount_span = item.find('span', class_='ingre_list_ea')
                            amount = self.clean_text(amount_span.text) if amount_span else '적당량'
                            
                            # 유효성 검사
                            if self._is_valid_ingredient(name, amount):
                                ingredients.append({
                                    'name': name,
                                    'amount': self.normalize_amount(amount),
                                    'group': current_group
                                })
                                
                        except Exception as e:
                            logger.error(f"재료 항목 파싱 중 오류: {str(e)}")
                            continue
        
        return ingredients  

    def _parse_ingredients_from_text(self, content: str) -> List[Dict[str, str]]:
        """텍스트에서 재료 정보 추출"""
        ingredients = []
        
        try:
            # 재료 섹션 찾기
            sections = []
            if '[재료]' in content:
                text = content.split('[재료]')[1]
                sections.append(('주재료', text))
                
                # 양념 섹션이 있는 경우
                if '[양념]' in text:
                    main_part = text.split('[양념]')[0]
                    sauce_part = text.split('[양념]')[1]
                    sections = [('주재료', main_part), ('양념', sauce_part)]
            
            for group_name, section_text in sections:
                # 쉼표나 줄바꿈으로 구분된 항목 처리
                items = [item.strip() for item in section_text.split(',')]
                for item in items:
                    if not item or len(item) < 3:
                        continue
                    
                    parts = item.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        amount = ' '.join(parts[1:])
                        
                        # 유효성 검사
                        if self._is_valid_ingredient(name, amount):
                            ingredients.append({
                                'name': name,
                                'amount': self.normalize_amount(amount),
                                'group': group_name
                            })
        
        except Exception as e:
            logger.error(f"텍스트 재료 파싱 중 오류: {str(e)}")
        
        return ingredients

    def _is_collection_post(self, title: str, description: str) -> bool:
        """모음집/리스트성 글인지 판단"""
        text = (title + ' ' + description).lower()
        return any(keyword in text.lower() for keyword in self.COLLECTION_KEYWORDS)

    def _is_valid_ingredient(self, name: str, amount: str) -> bool:
        """유효한 재료인지 검증"""
        if not name or len(name) < 2:
            return False
            
        # 특수문자 포함 체크
        if any(c in name for c in ['\x07', '@', '▶', '>']):
            return False
            
        # 잘못된 재료명 키워드 체크
        invalid_keywords = ['레시피', '보러가기', '구매', '참고', '클릭']
        if any(keyword in name.lower() for keyword in invalid_keywords):
            return False
            
        # 제목스러운 텍스트 체크
        if name.endswith(('편', '법', '팁', '때', '시')):
            return False
            
        return True

    def parse_steps(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """조리 단계 파싱"""
        steps = []
        step_items = soup.select("div.view_step_cont")
        
        for idx, item in enumerate(step_items, 1):
            try:
                description_el = item.select_one("div.media-body") or item
                if description_el:
                    description = self.clean_text(description_el.text)
                    if description:
                        steps.append({
                            'step_num': idx,
                            'description': description
                        })
            except Exception as e:
                logger.error(f"조리 단계 파싱 중 오류: {e}")
                continue
        
        return steps

    def parse_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """메타데이터 파싱"""
        metadata = {}
        
        try:
            # 시간 정보 추출
            time_elem = soup.select_one("span.view2_summary_info2")
            if time_elem:
                metadata['time'] = self.normalize_time(time_elem.text)
            
            # 난이도 추출
            difficulty_elem = soup.select_one("span.view2_summary_info3")
            if difficulty_elem:
                metadata['difficulty'] = self.normalize_difficulty(difficulty_elem.text)
            
            # 분량 추출
            servings_elem = soup.select_one("span.view2_summary_info1")
            if servings_elem:
                text = self.clean_text(servings_elem.text)
                servings_match = re.search(r'(\d+)인분', text)
                if servings_match:
                    metadata['servings'] = int(servings_match.group(1))
            
        except Exception as e:
            logger.error(f"메타데이터 파싱 중 오류: {str(e)}")
            
        return metadata

# Part 1: 기본 파싱 기능 (제목과 메타데이터)
class NaverRecipeParser(BaseRecipeParser):
    def parse_title(self, soup: BeautifulSoup) -> str:
        """레시피 제목 파싱"""
        title_element = soup.select_one('div.headword_title h2, div.article_head h2')
        if title_element:
            title = title_element.text.strip()
            if '(' in title:
                title = title.split('(')[0].strip()
            return title
        return ""

    def parse_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """메타데이터(조리시간, 난이도 등) 파싱"""
        metadata = {
            'time': {'original': '', 'minutes': None},
            'difficulty': {'original': '초급', 'level': 1},
            'servings': {'original': '1인분', 'servings': 1}
        }
        
        content = soup.get_text()
        
        try:
            sections = ['기본정보', '요리정보', '조리시간']
            for section in sections:
                section_idx = content.find(section)
                if section_idx != -1:
                    section_text = content[section_idx:section_idx + 500]
                    
                    # 조리시간 추출
                    time_pattern = re.compile(r'(?:조리|준비)?시간[^\d]*(\d+분|\d+시간(?:\s*\d+분)?)')
                    if time_match := time_pattern.search(section_text):
                        metadata['time'] = self.normalize_time(time_match.group(1))
                    
                    # 난이도 추출
                    difficulty_pattern = re.compile(r'난이도[^\w]*(초급|중급|고급|아무나|보통|어려움)')
                    if diff_match := difficulty_pattern.search(section_text):
                        metadata['difficulty'] = self.normalize_difficulty(diff_match.group(1))
                    
                    # 분량 추출
                    servings_pattern = re.compile(r'분량[^\d]*(\d+)(?:인분|개분|인용|servings?)')
                    if serv_match := servings_pattern.search(section_text):
                        servings = int(serv_match.group(1))
                        metadata['servings'] = {
                            'original': f"{servings}인분",
                            'servings': servings
                        }
                    break
            return metadata
        except Exception as e:
            logger.error(f"메타데이터 파싱 중 오류 발생: {str(e)}")
            return metadata

# Part 2: 재료 파싱 관련 기능
    def parse_ingredients(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """재료 정보 파싱 개선"""
        logger.info("=== 재료 파싱 시작 ===")
        
        ingredients = []
        seen_ingredients = set()
        
        try:
            content = soup.get_text()
            
            # 1. 재료 섹션 찾기
            ingredient_sections = [
                '주재료', '재료', '필요한 재료', '기본재료',
                '양념', '양념재료', '소스재료', '곁들임재료'
            ]
            
            for section in ingredient_sections:
                section_idx = content.find(section)
                if section_idx != -1:
                    # 다음 섹션까지의 텍스트 추출
                    next_idx = float('inf')
                    for next_section in ['만드는 법', '조리법', '영양성분']:
                        temp_idx = content.find(next_section, section_idx)
                        if temp_idx != -1:
                            next_idx = min(next_idx, temp_idx)
                    
                    if next_idx == float('inf'):
                        section_text = content[section_idx:section_idx + 500]
                    else:
                        section_text = content[section_idx:next_idx]
                    
                    # 재료 추출
                    ingredients.extend(self._extract_ingredients_from_text(section_text, section))
            
            # 2. 재료가 발견되지 않은 경우 본문에서 추출
            if not ingredients:
                ingredients = self._extract_ingredients_from_text(content, '주재료')
            
            # 3. 중복 제거 및 정제
            final_ingredients = []
            for ingredient in ingredients:
                if ingredient['name'] not in seen_ingredients:
                    seen_ingredients.add(ingredient['name'])
                    final_ingredients.append(ingredient)
            
            logger.info(f"총 {len(final_ingredients)}개의 재료를 추출했습니다")
            return final_ingredients
            
        except Exception as e:
            logger.error(f"재료 파싱 중 오류 발생: {str(e)}")
            return []
        
    def extract_ingredients_from_text(self, text: str, section: str = '주재료') -> List[Dict]:
        """텍스트에서 재료 정보 추출 - 개선된 버전"""
        ingredients = []
        
        # 재료 섹션을 찾는 키워드
        section_keywords = {
            "주재료": ["주재료", "필수재료", "기본재료"],
            "부재료": ["부재료", "선택재료", "곁들임재료"],
            "양념": ["양념", "소스", "양념장", "드레싱"]
        }
        
        # 무시할 키워드 리스트
        ignore_keywords = [
            # 메타데이터
            "조리시간", "분량", "칼로리", "보관온도", "보관기간", "보관법",
            # 섹션 헤더
            "요리과정", "기본정보", "재료설명", "요리법", "영양정보",
            # 설명 텍스트
            "먼저", "그리고", "넣고", "깔고", "다음", "마지막",
            # 동사형 키워드
            "씻어", "썰어", "넣어", "볶아", "담아",
            # 기타 텍스트
            "기준", "약간", "적당량", "유익해요", "싶어요", "담아갈게요", "수정해주세요"
        ]

        # 유효한 재료 단위
        valid_units = [
            'g', 'kg', 'ml', 'l', '컵', '큰술', '작은술', '개',
            '장', '마리', '포기', '줄', '조각', '쪽', '알', 'cm',
            '봉지', '캔', '팩', '통', '묶음', '줌', '꼬집', '주먹'
        ]

        # 재료 패턴 매칭
        patterns = [
            r'([가-힣a-zA-Z]+)\s*[:]?\s*(\d+(?:/\d+)?(?:\.\d+)?)\s*([가-힣a-zA-Z]+)?',  # 재료: 수량 단위
            r'([가-힣a-zA-Z]+)\s*\(([^)]+)\)',  # 재료(수량)
            r'([가-힣a-zA-Z]+)\s+(\d+(?:/\d+)?(?:\.\d+)?)\s*([가-힣a-zA-Z]+)?'  # 재료 수량 단위
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group(1).strip()
                
                # 무시할 키워드 체크
                if (name in ignore_keywords or
                    any(keyword in name for keyword in ignore_keywords) or
                    len(name) < 2):
                    continue

                # 재료명이 섹션 키워드인 경우 스킵
                if any(name in keywords for keywords in section_keywords.values()):
                    continue

                amount = match.group(2)
                unit = match.group(3) if len(match.groups()) > 2 else None

                # 단위가 유효한지 확인
                if unit and not any(valid_unit in unit for valid_unit in valid_units):
                    continue

                # 재료가 실제 식재료인지 확인
                if self._is_valid_ingredient(name):
                    ingredients.append({
                        'name': name,
                        'amount': self.normalize_amount(f"{amount}{unit if unit else ''}"),
                        'section': section
                    })

        return ingredients

    _extract_ingredients_from_text = extract_ingredients_from_text
    
    def _find_ingredients_in_content(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """본문에서 재료 정보 찾기"""
        ingredients = []
        seen_ingredients = set()
        
        try:
            txt_elements = soup.find_all('p', class_='txt')
            current_section = '주재료'
            
            for p in txt_elements:
                if strong := p.find('strong'):
                    section_text = strong.text.strip('· :')
                    if any(keyword in section_text for keyword in ['재료', '주재료', '부재료', '양념']):
                        current_section = section_text if '주재료' not in section_text else '주재료'
                        
                        ingredients_data = []
                        for a in p.find_all('a'):
                            name = self._clean_ingredient_name(a.text)
                            if name and self._is_valid_ingredient(name):
                                next_node = a.next_sibling
                                amount = ''
                                while next_node and isinstance(next_node, NavigableString):
                                    amount += next_node.string.strip()
                                    next_node = next_node.next_sibling
                                
                                if not amount:
                                    next_span = a.find_next('span', {'data-type': 'ore'})
                                    if next_span:
                                        amount = next_span.text.strip('() ,')
                                
                                if not amount:
                                    amount = '적당량'
                                    
                                ingredients_data.append((name, amount))
                        
                        for name, amount in ingredients_data:
                            if name not in seen_ingredients:
                                ingredients.append({
                                    'name': name,
                                    'amount': self.normalize_amount(amount),
                                    'section': current_section
                                })
                                seen_ingredients.add(name)
            return ingredients
                                
        except Exception as e:
            logger.error(f"재료 섹션 파싱 중 오류: {str(e)}")
            return []

    def _extract_ingredients_from_steps(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """조리 단계에서 재료 추출"""
        ingredients = []
        seen_ingredients = set()
        steps_text = ''
        
        try:
            # 1. 조리 단계 텍스트 수집
            for step in soup.find_all(['div', 'p'], 
                class_=lambda x: x and any(keyword in str(x).lower() 
                    for keyword in ['step', 'process', 'cooking', 'recipe_step'])):
                steps_text += step.get_text() + ' '

            if not steps_text:  # 일반 텍스트로도 시도
                steps_text = soup.get_text()

            # 2. 공통 재료 사전 (재료: [가능한 단위들])
            ingredient_patterns = {
                '우유': {
                    'units': ['ml', 'L', '리터', '컵', 'cc'],
                    'default': '200ml'
                },
                '생크림': {
                    'units': ['ml', 'L', '리터', '컵', 'cc'],
                    'default': '200ml'
                },
                '레몬': {
                    'units': ['개', '알', '조각', '반'],
                    'default': '1개'
                },
                '소금': {
                    'units': ['g', '그램', '큰술', '작은술', '꼬집', '스푼', '티스푼'],
                    'default': '약간'
                },
                '설탕': {
                    'units': ['g', '그램', '큰술', '작은술', '스푼', '티스푼'],
                    'default': '약간'
                },
                '베이킹소다': {
                    'units': ['g', '그램', '큰술', '작은술', '스푼', '티스푼'],
                    'default': '약간'
                }
            }

            # 3. 재료 추출
            for ingredient, info in ingredient_patterns.items():
                if ingredient in steps_text and ingredient not in seen_ingredients:
                    amount = info['default']  # 기본값 설정
                    
                    # 수량 패턴 찾기
                    start_idx = steps_text.find(ingredient)
                    if start_idx != -1:
                        # 재료 주변 텍스트 검사 (앞뒤 40자)
                        surrounding_text = steps_text[max(0, start_idx-40):min(len(steps_text), start_idx+40)]
                        
                        # 단위별로 수량 패턴 검색
                        for unit in info['units']:
                            pattern = f'\\d+(?:/\\d+)?(?:\\.\\d+)?\\s*{unit}'
                            if match := re.search(pattern, surrounding_text):
                                amount = match.group().strip()
                                break
                                
                            # "반" 처리
                            if '반' in surrounding_text and unit in ['개', '알']:
                                amount = '1/2개'
                                break

                    ingredients.append({
                        'name': ingredient,
                        'amount': self.normalize_amount(amount),
                        'section': '주재료'
                    })
                    seen_ingredients.add(ingredient)

            logger.info(f"조리 단계에서 {len(ingredients)}개의 재료를 추출했습니다.")
            return ingredients

        except Exception as e:
            logger.error(f"조리 단계에서 재료 추출 중 오류 발생: {str(e)}")
            logger.error(traceback.format_exc())
            return []

# Part 3: 유틸리티 함수들
    def _is_valid_ingredient(self, name: str) -> bool:
        """재료명 유효성 검증 - 개선된 버전"""
        if not name or len(name) < 2:
            return False

        # 일반적인 조리 동작 키워드
        cooking_actions = ['넣기', '썰기', '볶기', '무치기', '자르기', '담기', '섞기']
        if any(action in name for action in cooking_actions):
            return False

        # 섹션 헤더나 메타데이터
        headers = ['재료', '준비물', '양념', '소스', '메모', '팁', '과정', '정보']
        if any(header in name for header in headers):
            return False

        # 일반적인 식재료 목록
        common_ingredients = {
            # 채소류
            '양파', '마늘', '파', '당근', '감자', '고구마', '무', '배추',
            '시금치', '상추', '깻잎', '부추', '미나리', '콩나물', '숙주',
            
            # 육류
            '돼지고기', '소고기', '닭고기', '오리고기', '계란', '달걀',
            
            # 해산물
            '새우', '고등어', '멸치', '굴', '조개', '미역', '김',
            
            # 양념류
            '소금', '설탕', '후추', '간장', '된장', '고추장', '참기름',
            '들기름', '식용유', '마요네즈', '케첩',
            
            # 가공식품
            '두부', '어묵', '라면', '떡', '김치', '단무지',
            
            # 과일/견과류
            '밤', '대추', '땅콩', '호두', '잣'
        }

        # 식재료 접미사
        ingredient_suffixes = ['가루', '즙', '육', '살', '알', '잎', '면']

        return (name in common_ingredients or
                any(suffix in name for suffix in ingredient_suffixes) or
                re.match(r'^[가-힣]{2,}$', name))

    def _clean_ingredient_name(self, name: str) -> str:
        """재료명 정제"""
        if not name:
            return ''
        
        # 괄호와 내용 제거 (설명 텍스트)
        name = re.sub(r'\([^)]*\)', '', name)
        # 특수문자 및 공백 처리
        name = name.strip('· ,"\'')
        # 숫자와 단위 제거
        name = re.sub(r'\d+(?:\.\d+)?(?:g|ml|L|개|ml|큰술|작은술|컵)?$', '', name)
        
        return name.strip()

    def _clean_amount(self, text: str) -> str:
        """수량 정보 정제"""
        if not text:
            return '적당량'
            
        # 괄호 안의 숫자 추출
        if '(' in text and ')' in text:
            bracket_match = re.search(r'\(([^()]+)\)', text)
            if bracket_match:
                amount = bracket_match.group(1)
                if re.search(r'\d+(?:\.\d+)?(?:g|ml|L|개|ml|큰술|작은술|컵)?', amount):
                    return amount.strip()

        # 일반 텍스트에서 수량 추출
        amount_match = re.search(r'(\d+(?:/\d+)?(?:\s*(?:g|ml|L|개|ml|큰술|작은술|컵))?)', text)
        if amount_match:
            return amount_match.group(1).strip()

        return '적당량'
    # Part 4: 조리 단계 파싱 및 텍스트 정제

    def parse_steps(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """조리 단계 파싱 개선"""
        steps = []
        step_num = 1
        
        try:
            # 1. 본문 전체 텍스트 가져오기
            content = soup.get_text()
            
            # 2. 조리 과정 섹션 찾기
            process_keywords = ['조리법', '만드는 법', '조리과정', '요리법', '레시피']
            section_text = ''
            
            for keyword in process_keywords:
                start_idx = content.find(keyword)
                if start_idx != -1:
                    # 다음 섹션 시작 또는 끝까지
                    next_section_idx = float('inf')
                    for next_keyword in ['영양성분', '참고사항', '보관방법', '관련용어']:
                        temp_idx = content.find(next_keyword, start_idx)
                        if temp_idx != -1:
                            next_section_idx = min(next_section_idx, temp_idx)

                    if next_section_idx == float('inf'):
                        section_text = content[start_idx:]
                    else:
                        section_text = content[start_idx:next_section_idx]
                    break
            
            if not section_text:
                # 백업: 전체 텍스트에서 단계별 설명 찾기
                section_text = content
            
            # 3. 단계별 설명 추출
            # 3.1 번호로 시작하는 단계
            number_patterns = [
                r'(?:^|\n)\s*(\d+)[\.|\、|\)]\s*([^\n]+)',  # 1. 또는 1) 형식
                r'(?:^|\n)\s*Step\s*(\d+)\s*[\.|\:|\)]\s*([^\n]+)',  # Step 1: 형식
                r'(?:^|\n)\s*[\(|\[]\s*(\d+)\s*[\)|\]]\s*([^\n]+)',  # (1) 또는 [1] 형식
            ]
            
            for pattern in number_patterns:
                matches = re.finditer(pattern, section_text, re.MULTILINE)
                for match in matches:
                    step_text = match.group(2).strip()
                    if self._is_valid_step(step_text):
                        steps.append({
                            'step_num': step_num,
                            'description': self._clean_text(step_text)
                        })
                        step_num += 1
            
            # 3.2 키워드로 구분된 단계
            if not steps:
                step_keywords = ['먼저', '그다음', '다음으로', '이어서', '마지막으로']
                current_text = ''
                
                for line in section_text.split('\n'):
                    line = line.strip()
                    if any(keyword in line for keyword in step_keywords) or len(current_text) > 200:
                        if current_text and self._is_valid_step(current_text):
                            steps.append({
                                'step_num': step_num,
                                'description': self._clean_text(current_text)
                            })
                            step_num += 1
                        current_text = line
                    else:
                        current_text += ' ' + line
                
                # 마지막 단계 추가
                if current_text and self._is_valid_step(current_text):
                    steps.append({
                        'step_num': step_num,
                        'description': self._clean_text(current_text)
                    })
            
            # 4. 단계 정제
            final_steps = []
            for step in steps:
                # 불필요한 설명이나 중복 제거
                if not any(keyword in step['description'].lower() for keyword in 
                    ['tip:', '참고:', '영양성분', '보관방법']):
                    final_steps.append(step)
            
            logger.info(f"총 {len(final_steps)}개의 조리 단계 파싱됨")
            return final_steps
            
        except Exception as e:
            logger.error(f"조리 단계 파싱 중 오류 발생: {str(e)}")
            return []
        
    def _is_valid_step(self, text: str) -> bool:
        """유효한 조리 단계인지 검증"""
        if not text or len(text) < 10:  # 너무 짧은 텍스트는 제외
            return False
            
        # 조리와 관련없는 섹션 제외
        invalid_sections = [
            '영양성분', '보관방법', '참고사항', '관련용어',
            '출처', '자세한 정보', '본문', '목차'
        ]
        if any(section in text for section in invalid_sections):
            return False
        
        # 조리 동작 키워드가 포함된 경우 유효한 단계로 판단
        cooking_keywords = [
            '넣', '섞', '볶', '끓', '자르', '썰', '담', '두',
            '말', '식히', '데치', '졸이', '버무리', '굽', '찌',
            '삶', '건지', '식혀', '무치', '양념', '다지', '저어'
        ]
        
        return any(keyword in text for keyword in cooking_keywords)

    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        
        try:
            # 1. 기본 공백 제거
            text = text.strip()
            
            # 2. 연속된 공백을 하나로
            text = re.sub(r'\s+', ' ', text)
            
            # 3. HTML 엔티티 변환
            text = text.replace('&nbsp;', ' ')
            text = html.unescape(text)
            
            # 4. 특수문자 처리
            text = text.replace('●', '').replace('■', '').replace('※', '')
            text = text.replace('☞', '').replace('▶', '').replace('▷', '')
            
            # 5. 불필요한 문장 제거
            skip_phrases = ['클릭하시면', '자세한 정보', '참고하세요', '추천해요']
            for phrase in skip_phrases:
                text = text.replace(phrase, '')
            
            # 6. 최종 공백 정리
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.error(f"텍스트 정제 중 오류 발생: {str(e)}, 원본 텍스트: {text}")
            return text.strip()
        

    def normalize_amount(self, amount_str: str) -> Dict[str, Any]:
        """수량 정보 정규화 - 개선된 버전"""
        if not amount_str:
            return {'original': '', 'value': None, 'unit': None}
            
        result = {'original': amount_str, 'value': None, 'unit': None}
        
        # 숫자 패턴
        number_pattern = r'\d+(?:/\d+)?(?:\.\d+)?'
        
        # 분수 처리
        fraction_match = re.search(r'(\d+)/(\d+)', amount_str)
        if fraction_match:
            numerator = int(fraction_match.group(1))
            denominator = int(fraction_match.group(2))
            result['value'] = numerator / denominator
        else:
            # 일반 숫자 찾기
            number_match = re.search(number_pattern, amount_str)
            if number_match:
                number_str = number_match.group()
                # 분수 형태 처리
                if '/' in number_str:
                    num, denom = map(int, number_str.split('/'))
                    result['value'] = num / denom
                else:
                    result['value'] = float(number_str)

        # 단위 처리
        units = {
            '중량': ['g', 'kg', '근', 'mg'],
            '부피': ['ml', 'l', '컵', '종이컵', '밥숟가락', '스푼', '큰술', '작은술'],
            '개수': ['개', '알', '조각', '장', '포기', '마리', '톨', '통', '묶음', 
                   '봉지', '봉', '팩', '캔'],
            '길이': ['cm', 'm', 'mm'],
            '기타': ['꼬집', '줌', '주먹', '다시', '움큼', '약간', '적당량']
        }

        for unit_type in units.values():
            for unit in unit_type:
                if unit in amount_str:
                    result['unit'] = unit
                    break
            if result['unit']:
                break

        return result
