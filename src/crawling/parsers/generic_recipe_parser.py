from bs4 import BeautifulSoup
import re
from typing import Dict, List, Any
import logging

class GenericRecipeParser:
    """다양한 레시피 사이트를 지원하는 범용 파서"""
    
    def __init__(self):
        self.logger = logging.getLogger('GenericRecipeParser')
        
        # 일반적인 레시피 관련 키워드
        self.recipe_keywords = [
            '재료', '만드는 법', '조리법', '레시피', '요리 방법', 
            '준비 재료', '만들기', '조리 과정', '조리 순서'
        ]
        
        # 일반적인 단계 표현
        self.step_indicators = [
            r'\d+[\.|\、|\)]', r'STEP\s*\d+', r'[\(|\[]\s*\d+\s*[\)|\]]',
            r'단계\s*\d+', r'과정\s*\d+', r'순서\s*\d+'
        ]
        
        # 일반적인 재료 단위
        self.ingredient_units = [
            'g', 'kg', 'ml', 'l', '컵', '큰술', '작은술', '개', 
            '마리', '조각', '스푼', '숟가락', '봉지', '줌'
        ]
    
    def parse_title(self, soup: BeautifulSoup) -> str:
        """레시피 제목 추출 시도"""
        try:
            # 1. 일반적인 제목 태그
            for selector in ['h1', 'h2', 'title', '.recipe-title', '.title', '.main-title']:
                elements = soup.select(selector)
                for element in elements:
                    title = element.text.strip()
                    if len(title) > 3 and len(title) < 100:
                        # 제목스러운지 확인 (레시피, 만들기 등 키워드 포함)
                        if any(keyword in title.lower() for keyword in ['레시피', '요리', '만들기', '만드는']):
                            return title
            
            # 2. 메타 태그
            og_title = soup.find('meta', {'property': 'og:title'})
            if og_title and 'content' in og_title.attrs:
                return og_title['content'].strip()
                
            # 3. 큰 텍스트 요소 중 레시피 관련 키워드가 있는 것
            for tag in soup.find_all(['h3', 'h4', 'strong', 'b']):
                text = tag.text.strip()
                if len(text) > 3 and len(text) < 100:
                    if any(keyword in text.lower() for keyword in ['레시피', '요리', '만들기']):
                        return text
            
            # 4. 페이지 제목
            if soup.title:
                return soup.title.text.strip()
                
            return "제목을 찾을 수 없습니다"
            
        except Exception as e:
            self.logger.error(f"제목 파싱 중 오류: {str(e)}")
            return "제목 파싱 오류"
    
    def parse_ingredients(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """재료 목록 추출 시도"""
        ingredients = []
        
        try:
            # 1. 재료 섹션 찾기
            ingredient_section = None
            
            # 1.1 일반적인 재료 섹션 클래스
            for selector in ['.ingredients', '.recipe-ingredients', '.ingredient-list', '#ingredients']:
                section = soup.select_one(selector)
                if section:
                    ingredient_section = section
                    break
            
            # 1.2 특정 제목/키워드가 있는 섹션 찾기
            if not ingredient_section:
                for heading in soup.find_all(['h2', 'h3', 'h4', 'strong', 'b']):
                    if any(keyword in heading.text.lower() for keyword in ['재료', '준비', '준비물']):
                        # 다음 ul/ol 요소 또는 다음 div 찾기
                        section = heading.find_next(['ul', 'ol', 'div'])
                        if section:
                            ingredient_section = section
                            break
            
            # 2. 재료 섹션에서 항목 추출
            if ingredient_section:
                # 2.1 리스트 항목
                list_items = ingredient_section.find_all('li')
                if list_items:
                    for item in list_items:
                        ingredient = self._parse_ingredient_text(item.text.strip())
                        if ingredient:
                            ingredients.append(ingredient)
                
                # 2.2 리스트 없으면 줄 단위로 분리
                elif ingredient_section.text:
                    lines = ingredient_section.text.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 2 and not any(heading in line.lower() for heading in ['재료', '준비물']):
                            ingredient = self._parse_ingredient_text(line)
                            if ingredient:
                                ingredients.append(ingredient)
            
            # 3. 전체 페이지에서 재료 패턴 찾기
            if not ingredients:
                # 텍스트에서 "재료" 섹션을 찾아 파싱
                full_text = soup.get_text()
                match = re.search(r'(재료|준비물|준비 재료)[^\n]*\n(.*?)(?:만드는 법|조리법|만들기|레시피)', 
                                full_text, re.DOTALL)
                if match:
                    ingredient_text = match.group(2)
                    lines = ingredient_text.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 2:
                            ingredient = self._parse_ingredient_text(line)
                            if ingredient:
                                ingredients.append(ingredient)
            
            return ingredients
            
        except Exception as e:
            self.logger.error(f"재료 파싱 중 오류: {str(e)}")
            return []
    
    def _parse_ingredient_text(self, text: str) -> Dict[str, Any]:
        """재료 텍스트에서 이름과 양 추출"""
        text = text.strip()
        if not text or len(text) < 2:
            return None
            
        # 1. 콜론(:)으로 분리된 경우
        if ':' in text:
            name, amount = text.split(':', 1)
            return {
                'name': name.strip(),
                'amount': {'original': amount.strip()},
                'group': '주재료'
            }
            
        # 2. 수량 패턴 매칭
        # 재료 [숫자+단위] 패턴
        match = re.search(r'([가-힣a-zA-Z]+)\s*(\d+(?:\.\d+)?)\s*([가-힣a-zA-Z]+)?', text)
        if match:
            name = match.group(1).strip()
            value = match.group(2)
            unit = match.group(3) if match.group(3) else ''
            
            # 유효한 단위인지 확인
            if unit and any(u == unit or u in unit for u in self.ingredient_units):
                return {
                    'name': name,
                    'amount': {
                        'original': f"{value}{unit}",
                        'value': float(value) if value else None,
                        'unit': unit
                    },
                    'group': '주재료'
                }
        
        # 3. 기타 패턴
        # 마지막 수단: 공백으로 분리하고 마지막 단어가 단위인지 확인
        words = text.split()
        if len(words) >= 2:
            last_word = words[-1]
            if any(u in last_word for u in self.ingredient_units) or re.search(r'\d+', last_word):
                name = ' '.join(words[:-1])
                return {
                    'name': name,
                    'amount': {'original': last_word},
                    'group': '주재료'
                }
        
        # 단위 없는 경우: 재료명만 반환
        return {
            'name': text,
            'amount': {'original': '적당량'},
            'group': '주재료'
        }
    
    def parse_steps(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """조리 단계 추출 시도"""
        steps = []
        
        try:
            # 1. 단계별 구조 있는 경우
            step_section = None
            
            # 1.1 일반적인 단계 섹션 클래스
            for selector in ['.instructions', '.recipe-steps', '.steps', '.directions', '#instructions']:
                section = soup.select_one(selector)
                if section:
                    step_section = section
                    break
            
            # 1.2 특정 제목/키워드가 있는 섹션 찾기
            if not step_section:
                for heading in soup.find_all(['h2', 'h3', 'h4', 'strong', 'b']):
                    if any(keyword in heading.text.lower() for keyword in ['만드는 법', '조리법', '만들기', '조리 순서']):
                        # 다음 ul/ol 요소 또는 다음 div 찾기
                        section = heading.find_next(['ul', 'ol', 'div'])
                        if section:
                            step_section = section
                            break
            
            # 2. 단계 섹션에서 항목 추출
            if step_section:
                # 2.1 리스트 항목
                list_items = step_section.find_all('li')
                if list_items:
                    for idx, item in enumerate(list_items, 1):
                        steps.append({
                            'step_num': idx,
                            'description': item.text.strip()
                        })
                
                # 2.2 단계별 클래스가 있는 경우
                step_items = step_section.select('[class*="step"]')
                if not steps and step_items:
                    for idx, item in enumerate(step_items, 1):
                        steps.append({
                            'step_num': idx,
                            'description': item.text.strip()
                        })
                
                # 2.3 단계 표시가 있는 텍스트
                if not steps:
                    text = step_section.text
                    for pattern in self.step_indicators:
                        step_matches = re.findall(f"{pattern}[^\n\r]*", text)
                        if step_matches:
                            for idx, match in enumerate(step_matches, 1):
                                steps.append({
                                    'step_num': idx,
                                    'description': match.strip()
                                })
                            break
            
            # 3. 전체 페이지에서 조리 단계 찾기
            if not steps:
                full_text = soup.get_text()
                
                # 3.1 "만드는 법" 섹션을 찾아 파싱
                match = re.search(r'(만드는 법|조리법|만들기|레시피)[^\n]*\n(.*?)(?:$|요리 팁|요리팁|주의사항)',
                                  full_text, re.DOTALL)
                if match:
                    steps_text = match.group(2)
                    
                    # 번호 매겨진 단계 찾기
                    step_lines = []
                    for pattern in self.step_indicators:
                        step_matches = re.findall(f"{pattern}[^\n\r]*", steps_text)
                        if step_matches:
                            step_lines = step_matches
                            break
                    
                    # 번호 없으면 줄 단위로 분리
                    if not step_lines:
                        step_lines = [line.strip() for line in steps_text.split('\n') 
                                    if line.strip() and len(line.strip()) > 5]
                    
                    for idx, line in enumerate(step_lines, 1):
                        steps.append({
                            'step_num': idx,
                            'description': line.strip()
                        })
            
            return steps
            
        except Exception as e:
            self.logger.error(f"조리 단계 파싱 중 오류: {str(e)}")
            return []
    
    def parse_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """메타데이터(조리시간, 난이도 등) 추출 시도"""
        metadata = {
            'time': {'original': '', 'minutes': None},
            'difficulty': {'original': '', 'level': None},
            'servings': {'original': '', 'servings': None}
        }
        
        try:
            # 전체 텍스트에서 패턴 찾기
            text = soup.get_text()
            
            # 1. 조리시간
            time_patterns = [
                r'소요\s*?시간[^\d]*(\d+)\s*분',
                r'조리\s*?시간[^\d]*(\d+)\s*분',
                r'시간[^\d]*(\d+)\s*분',
                r'(\d+)\s*분\s*소요',
                r'약\s*(\d+)\s*분'
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, text)
                if match:
                    minutes = int(match.group(1))
                    metadata['time'] = {
                        'original': match.group(0),
                        'minutes': minutes
                    }
                    break
            
            # 2. 난이도
            difficulty_patterns = [
                r'난이도[^\w]*(초급|중급|고급|어려움|보통|쉬움)',
                r'(초급|중급|고급)\s*난이도'
            ]
            
            for pattern in difficulty_patterns:
                match = re.search(pattern, text)
                if match:
                    difficulty_text = match.group(1)
                    level_map = {'초급': 1, '쉬움': 1, '보통': 2, '중급': 2, '고급': 3, '어려움': 3}
                    level = level_map.get(difficulty_text, None)
                    
                    metadata['difficulty'] = {
                        'original': difficulty_text,
                        'level': level
                    }
                    break
            
            # 3. 인분 수
            servings_patterns = [
                r'(\d+)인분',
                r'(\d+)\s*serving',
                r'(\d+)\s*persons?',
                r'(\d+)\s*명',
                r'인원[^\d]*(\d+)'
            ]
            
            for pattern in servings_patterns:
                match = re.search(pattern, text)
                if match:
                    servings = int(match.group(1))
                    metadata['servings'] = {
                        'original': match.group(0),
                        'servings': servings
                    }
                    break
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"메타데이터 파싱 중 오류: {str(e)}")
            return metadata