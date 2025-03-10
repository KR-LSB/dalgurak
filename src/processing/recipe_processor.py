from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import json
import re

class RecipeProcessor:
    """레시피 데이터 정규화 및 전처리 클래스"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.required_fields = {
            'title': '',
            'ingredients': [],
            'steps': [],
            'category': '기타',
            'metadata': {}
        }
        
        # 기본 메타데이터 구조
        self.default_metadata = {
            'time': {'original': '', 'minutes': None},
            'difficulty': {'original': '초급', 'level': 1},
            'servings': {'original': '1인분', 'servings': 1}
        }
        
        # 레시피 카테고리 매핑
        self.category_mapping = {
            '밥/죽/떡': ['밥', '죽', '떡', '한식'],
            '국/탕/찌개': ['국', '탕', '찌개', '전골'],
            '반찬': ['반찬', '구이', '조림', '볶음', '무침', '튀김'],
            '면/만두': ['면', '만두', '파스타', '스파게티'],
            '양식': ['스테이크', '파스타', '리조또', '샐러드'],
            '디저트': ['과자', '쿠키', '케이크', '빵'],
            '음료': ['주스', '차', '커피', '스무디']
        }

    def _setup_logger(self):
        logger = logging.getLogger('RecipeProcessor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 파일 핸들러
            fh = logging.FileHandler('recipe_processing.log')
            fh.setLevel(logging.INFO)
            
            # 콘솔 핸들러
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            # 포맷터
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            logger.addHandler(fh)
            logger.addHandler(ch)
            
        return logger

    def process_recipe(self, recipe: Dict) -> Dict:
        """개별 레시피 정규화"""
        try:
            # 기본 필드 확인 및 보완
            processed = self.required_fields.copy()
            processed.update(recipe)

            # 제목 처리
            processed['title'] = self._process_title(processed['title'])
            if not processed['title']:
                self.logger.warning(f"Recipe title missing: {recipe.get('url', 'Unknown URL')}")
                return None

            # 재료 처리
            processed['ingredients'] = self._process_ingredients(processed['ingredients'])
            if not processed['ingredients']:
                self.logger.warning(f"Recipe ingredients missing: {processed['title']}")
                return None

            # 조리 단계 처리
            processed['steps'] = self._process_steps(processed['steps'])
            if not processed['steps']:
                self.logger.warning(f"Recipe steps missing: {processed['title']}")
                return None

            # 카테고리 정규화
            processed['category'] = self._normalize_category(processed['category'])

            # 메타데이터 보완
            processed['metadata'] = self._process_metadata(processed.get('metadata', {}))

            # 검증
            if self._validate_recipe(processed):
                return processed
            return None

        except Exception as e:
            self.logger.error(f"Error processing recipe: {str(e)}")
            return None

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        if not isinstance(text, str):
            return ""
            
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # 특수문자 처리
        text = text.replace('&nbsp;', ' ')
        text = text.replace('\u200b', '')
        
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _process_title(self, title: str) -> str:
        """제목 처리 및 정규화"""
        if not title:
            return ''
            
        # 제목 정제
        title = self._normalize_text(title)
        
        # 불필요한 접미사 제거
        remove_suffixes = ['레시피', '만들기', ' 황금레시피', ' 만드는 법']
        for suffix in remove_suffixes:
            if title.endswith(suffix):
                title = title[:-len(suffix)]
        
        return title.strip()

    def _process_ingredients(self, ingredients: list) -> list:
        """재료 정보 처리 및 보완"""
        if not ingredients:
            return []

        processed_ingredients = []
        for ing in ingredients:
            if not isinstance(ing, dict):
                continue

            name = self._normalize_text(ing.get('name', ''))
            if not name:
                continue

            # 재료량 정규화
            amount_info = ing.get('amount', {})
            if isinstance(amount_info, str):
                amount_info = {'original': amount_info}
            
            processed_ingredient = {
                'name': name,
                'amount': self._normalize_amount(amount_info),
                'group': self._normalize_text(ing.get('group', '주재료'))
            }
            processed_ingredients.append(processed_ingredient)

        return processed_ingredients

    def _normalize_amount(self, amount: Dict) -> Dict:
        """재료 양 정규화"""
        normalized = {
            'original': '',
            'value': None,
            'unit': None
        }
        
        if not isinstance(amount, dict):
            return normalized
            
        # 원본 텍스트 처리
        original = str(amount.get('original', '')).strip()
        normalized['original'] = original
        
        # 수치 처리
        value = amount.get('value')
        if isinstance(value, (int, float)) and value > 0:
            normalized['value'] = value
        
        # 단위 처리
        unit = str(amount.get('unit', '')).strip()
        if unit:
            normalized['unit'] = self._normalize_unit(unit)
        
        return normalized

    def _normalize_unit(self, unit: str) -> str:
        """단위 정규화"""
        unit_mapping = {
            # 무게
            'g': 'g', '그램': 'g', 'gram': 'g',
            'kg': 'kg', '킬로': 'kg', '킬로그램': 'kg',
            
            # 부피
            'ml': 'ml', '미리리터': 'ml',
            'l': 'l', '리터': 'l',
            '컵': '컵', 'cup': '컵',
            '큰술': '큰술', '큰스푼': '큰술', '대스푼': '큰술',
            '작은술': '작은술', '찻술': '작은술', '소스푼': '작은술',
            
            # 개수
            '개': '개', '알': '개',
            '조각': '조각', '쪽': '조각',
            
            # 기타
            '꼬집': '꼬집',
            '줌': '줌',
            '적당량': '적당량',
            '약간': '약간'
        }
        
        return unit_mapping.get(unit.lower(), unit)

    def _process_steps(self, steps: list) -> list:
        """조리 단계 처리 및 보완"""
        if not steps:
            return []

        processed_steps = []
        step_num = 1
        
        for step in steps:
            if not isinstance(step, dict):
                continue

            description = self._normalize_text(step.get('description', ''))
            if not description:
                continue

            # 단계 내용 정제
            description = self._clean_step_description(description)
            
            processed_steps.append({
                'step_num': step_num,
                'description': description
            })
            step_num += 1

        return processed_steps
    
    def _normalize_category(self, category: str) -> str:
        """카테고리 정규화"""
        if not category:
            return '기타'

        category = self._normalize_text(category)
        
        # 카테고리 매핑
        for main_category, keywords in self.category_mapping.items():
            if any(keyword in category.lower() for keyword in keywords):
                return main_category

        return '기타'

    def _process_metadata(self, metadata: dict) -> dict:
        """메타데이터 처리 및 보완"""
        processed = self.default_metadata.copy()
        
        if not metadata:
            return processed

        # 조리 시간 처리
        if 'time' in metadata:
            processed['time'] = self._normalize_time(metadata['time'])

        # 난이도 처리
        if 'difficulty' in metadata:
            processed['difficulty'] = self._normalize_difficulty(metadata['difficulty'])

        # 분량 처리
        if 'servings' in metadata:
            processed['servings'] = self._normalize_servings(metadata['servings'])

        return processed

    def _clean_step_description(self, description: str) -> str:
        """조리 단계 설명 정제"""
        # 불필요한 문구 제거
        remove_phrases = ['팁:', 'TIP:', '참고:', '※']
        for phrase in remove_phrases:
            if phrase in description:
                description = description.split(phrase)[0]

        # 중복 공백 제거
        description = ' '.join(description.split())

        return description.strip()

    def _validate_recipe(self, recipe: dict) -> bool:
        """레시피 데이터 검증"""
        # 필수 필드 검증
        if not recipe.get('title') or not recipe.get('ingredients') or not recipe.get('steps'):
            return False

        # 재료 검증
        if len(recipe['ingredients']) < 1:
            return False

        # 조리 단계 검증
        if len(recipe['steps']) < 1:
            return False

        # 제목 길이 검증
        if len(recipe['title']) < 2 or len(recipe['title']) > 100:
            return False

        return True

    def _determine_situation(self, recipe: Dict) -> List[str]:
        """레시피의 상황 분류를 결정하는 메소드"""
        
        # 상황별 키워드 정의
        situation_keywords = {
            '손님접대': ['손님', '접대', '파티', '모임', '명절', '잔치'],
            '술안주': ['안주', '술안주', '맥주', '소주', '와인', '칵테일'],
            '다이어트': ['다이어트', '저칼로리', '건강식', '샐러드', '보신', '덜기름진'],
            '간식': ['간식', '디저트', '스낵', '과자', '쿠키', '빵', '케이크'],
            '야식': ['야식', '야참', '밤참', '늦은', '야명', '야식용'],
            '주말': ['주말', '브런치', '피크닉'],
            '초스피드': ['초스피드', '초간단', '간단', '빠른', '즉석', '3분', '5분', '10분', '15분'],
            '편의점음식': ['편의점', '즉석식품', '컵라면'],
            '도시락': ['도시락', '반찬', '김밥', '도착', '소풍'],
            '영양식': ['영양', '보양', '건강', '든든', '영양가', '단백질', '채소']
        }

        # 검색할 텍스트 준비
        search_text = ' '.join([
            recipe.get('url', '').lower(),
            recipe.get('title', '').lower(),
            ' '.join(step.get('description', '').lower() for step in recipe.get('steps', []))
        ])

        # 점수 기반 상황 판단
        situation_scores = {situation: 0 for situation in situation_keywords.keys()}
        
        for situation, keywords in situation_keywords.items():
            for keyword in keywords:
                if keyword in search_text:
                    # URL에서 발견되면 더 높은 가중치 부여
                    if keyword in recipe.get('url', '').lower():
                        situation_scores[situation] += 2
                    else:
                        situation_scores[situation] += 1
        
        # 점수가 있는 모든 상황 선택 (threshold = 1)
        selected_situations = [
            situation for situation, score in situation_scores.items()
            if score > 0
        ]
        
        # 특별한 카테고리 기반 상황 매핑
        category_to_situation = {
            '간식': '간식',
            '과자': '간식',
            '디저트': '간식',
            '양식': '손님접대',
            '퓨전': '손님접대',
            '양념/소스/잼': '영양식',
        }
        
        # 레시피의 카테고리를 기반으로 상황을 추가
        category = recipe.get('category', '')
        if category in category_to_situation:
            situation = category_to_situation[category]
            if situation not in selected_situations:
                selected_situations.append(situation)

        return selected_situations if selected_situations else ['기타']
    
    def _normalize_time(self, time_info: Dict) -> Dict:
        """조리시간 정규화"""
        normalized = {
            'original': '',
            'minutes': None
        }
        
        if not isinstance(time_info, dict):
            return normalized
            
        original = str(time_info.get('original', '')).strip()
        normalized['original'] = original
        
        minutes = time_info.get('minutes')
        if isinstance(minutes, (int, float)) and minutes > 0:
            normalized['minutes'] = int(minutes)
            
        return normalized

    def _normalize_difficulty(self, difficulty_info: Dict) -> Dict:
        """난이도 정규화"""
        normalized = {
            'original': '',
            'level': None
        }
        
        if not isinstance(difficulty_info, dict):
            return normalized
            
        original = str(difficulty_info.get('original', '')).strip()
        normalized['original'] = original
        
        level = difficulty_info.get('level')
        if isinstance(level, int) and level in [1, 2, 3]:
            normalized['level'] = level
            
        return normalized

    def _normalize_servings(self, servings_info: Dict) -> Dict:
        """분량 정규화"""
        normalized = {
            'original': '',
            'servings': None
        }
        
        if not isinstance(servings_info, dict):
            return normalized
            
        original = str(servings_info.get('original', '')).strip()
        normalized['original'] = original
        
        servings = servings_info.get('servings')
        if isinstance(servings, int) and servings > 0:
            normalized['servings'] = servings
            
        return normalized

    def process_recipes(self, recipes: List[Dict]) -> List[Dict]:
        """여러 레시피 일괄 처리"""
        processed_recipes = []
        total = len(recipes)
        
        self.logger.info(f"총 {total}개의 레시피 처리 시작")
        
        for idx, recipe in enumerate(recipes, 1):
            try:
                processed = self.process_recipe(recipe)
                processed_recipes.append(processed)
                
                if idx % 100 == 0:
                    self.logger.info(f"{idx}/{total} 레시피 처리 완료")
                    
            except Exception as e:
                self.logger.error(f"레시피 처리 실패 (ID: {recipe.get('id', 'unknown')}): {str(e)}")
                continue
                
        self.logger.info(f"총 {len(processed_recipes)}/{total} 레시피 처리 완료")
        return processed_recipes

    def save_processed_recipes(self, recipes: List[Dict], output_dir: Path = None):
        """처리된 레시피 저장"""
        if output_dir is None:
            output_dir = Path('data/processed')
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'processed_recipes_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"처리된 레시피를 {output_file}에 저장했습니다.")