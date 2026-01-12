"""
레시피 데이터 처리기

수집된 레시피 데이터의 정제, 구조화, 검증을 담당합니다.

Features:
    - 데이터 정제 및 정규화
    - 재료/단계 구조화
    - 난이도/조리시간 자동 추정
    - 카테고리 분류
    - 통계 분석

Example:
    >>> processor = RecipeProcessor(data_dir=Path('data/raw'))
    >>> recipes = processor.process_all_recipes()
    >>> print(processor.get_statistics())
"""

import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RecipeProcessor:
    """
    레시피 데이터 처리기
    
    수집된 원시 레시피 데이터를 정제하고 구조화합니다.
    처리된 데이터는 RAG 시스템의 벡터 DB에 저장됩니다.
    
    Args:
        data_dir: 원시 데이터 디렉토리 (기본값: data/raw)
    
    Attributes:
        processed_recipes: 처리된 레시피 목록
        statistics: 데이터 통계
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path('data/raw')
        self.processed_recipes: List[Dict] = []
        self.statistics: Dict[str, Any] = {}
        
        # 단위 정규화 매핑
        self.unit_mapping = {
            '큰술': 'tbsp', '작은술': 'tsp', '컵': 'cup',
            '개': 'ea', '쪽': 'ea', '줄기': 'ea', '장': 'ea',
            'g': 'g', 'kg': 'kg', 'ml': 'ml', 'L': 'L',
            '약간': 'some', '조금': 'some', '적당량': 'some', '적당히': 'some'
        }
        
        # 난이도 키워드
        self.difficulty_keywords = {
            '쉬움': ['간단', '쉬운', '초보', '빠른', '간편', '손쉬운', '금방'],
            '보통': ['기본', '일반', '보통'],
            '어려움': ['어려운', '복잡', '정성', '전문', '고급', '까다로운']
        }

    def process_all_recipes(self) -> List[Dict]:
        """
        모든 레시피 파일 처리
        
        data_dir 내의 모든 JSON 파일을 읽어 처리합니다.
        
        Returns:
            처리된 레시피 목록
        """
        if not self.data_dir.exists():
            logger.warning(f"데이터 디렉토리가 없음: {self.data_dir}")
            return []
            
        json_files = list(self.data_dir.glob('*.json'))
        
        if not json_files:
            logger.warning(f"JSON 파일이 없음: {self.data_dir}")
            return []

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    recipes = json.load(f)
                
                # 리스트가 아닌 경우 처리
                if isinstance(recipes, dict):
                    if 'recipes' in recipes:
                        recipes = recipes['recipes']
                    else:
                        recipes = [recipes]

                for recipe in recipes:
                    processed = self.process_recipe(recipe)
                    if processed:
                        self.processed_recipes.append(processed)

                logger.info(f"{json_file.name}에서 {len(recipes)}개 레시피 처리")

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류 ({json_file}): {str(e)}")
            except Exception as e:
                logger.error(f"파일 처리 중 오류 ({json_file}): {str(e)}")

        self._calculate_statistics()
        logger.info(f"총 {len(self.processed_recipes)}개 레시피 처리 완료")
        return self.processed_recipes

    def process_recipe(self, recipe: Dict) -> Optional[Dict]:
        """
        개별 레시피 처리
        
        Args:
            recipe: 원시 레시피 데이터
            
        Returns:
            처리된 레시피 또는 None (유효하지 않은 경우)
        """
        try:
            processed = {
                'id': self._generate_id(recipe),
                'title': self._clean_title(recipe.get('title', '')),
                'category': recipe.get('category', '기타'),
                'source': recipe.get('source', 'unknown'),
                'url': recipe.get('url', ''),
                'ingredients': self._process_ingredients(recipe.get('ingredients', [])),
                'steps': self._process_steps(recipe.get('steps', [])),
                'difficulty': self._estimate_difficulty(recipe),
                'cooking_time': self._estimate_cooking_time(recipe),
                'servings': self._extract_servings(recipe),
                'description': recipe.get('description', ''),
                'processed_at': datetime.now().isoformat()
            }

            # 유효성 검사
            is_valid, errors = RecipeValidator.validate(processed)
            if not is_valid:
                logger.debug(f"레시피 검증 실패: {errors}")
                return None

            return processed

        except Exception as e:
            logger.error(f"레시피 처리 중 오류: {str(e)}")
            return None

    def _generate_id(self, recipe: Dict) -> str:
        """레시피 고유 ID 생성 (MD5 해시 기반)"""
        content = f"{recipe.get('title', '')}{recipe.get('url', '')}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _clean_title(self, title: str) -> str:
        """제목 정제"""
        if not title:
            return ""
        
        # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
        title = re.sub(r'[^\w\s가-힣]', ' ', title)
        # 연속 공백 제거
        title = re.sub(r'\s+', ' ', title)
        return title.strip()

    def _process_ingredients(self, ingredients: List) -> List[Dict]:
        """
        재료 정보 구조화
        
        Args:
            ingredients: 재료 문자열 리스트
            
        Returns:
            구조화된 재료 정보 리스트
        """
        processed = []

        for ing in ingredients:
            if not ing:
                continue
                
            # 문자열인 경우
            if isinstance(ing, str):
                ing_text = ing.strip()
                if ing_text:
                    parsed = self._parse_ingredient(ing_text)
                    if parsed:
                        processed.append(parsed)
            # 이미 딕셔너리인 경우
            elif isinstance(ing, dict):
                processed.append({
                    'name': ing.get('name', str(ing)),
                    'amount': ing.get('amount', ''),
                    'unit': ing.get('unit', ''),
                    'original': ing.get('original', str(ing))
                })

        return processed

    def _parse_ingredient(self, ingredient: str) -> Optional[Dict]:
        """
        재료 문자열 파싱
        
        "돼지고기 300g" -> {"name": "돼지고기", "amount": "300", "unit": "g"}
        """
        try:
            # 공백 정규화
            ingredient = re.sub(r'\s+', ' ', ingredient.strip())
            
            # 양 추출 패턴: "재료명 숫자단위" 또는 "재료명 숫자 단위"
            pattern = r'^([가-힣a-zA-Z\s]+?)\s*(\d+(?:\.\d+)?)\s*(큰술|작은술|컵|개|쪽|장|줄기|g|kg|ml|L|약간|조금|적당량)?$'
            match = re.match(pattern, ingredient)

            if match:
                name = match.group(1).strip()
                amount = match.group(2) or ''
                unit = match.group(3) or ''
                
                # 단위 정규화
                normalized_unit = self.unit_mapping.get(unit, unit)
                
                return {
                    'name': name,
                    'amount': amount,
                    'unit': normalized_unit,
                    'original': ingredient
                }
            
            # 패턴 매칭 실패 시 원본 유지
            return {
                'name': ingredient,
                'amount': '',
                'unit': '',
                'original': ingredient
            }

        except Exception:
            return None

    def _process_steps(self, steps: List) -> List[Dict]:
        """
        조리 단계 구조화
        
        Args:
            steps: 조리 단계 문자열 리스트
            
        Returns:
            구조화된 조리 단계 리스트
        """
        processed = []

        for i, step in enumerate(steps, 1):
            if not step:
                continue
                
            step_text = step if isinstance(step, str) else str(step)
            step_text = step_text.strip()
            
            if not step_text:
                continue
            
            # 번호 제거 (이미 순서가 있는 경우)
            step_text = re.sub(r'^\d+[\.\)]\s*', '', step_text)

            processed.append({
                'order': i,
                'description': step_text,
                'duration': self._extract_duration(step_text)
            })

        return processed

    def _extract_duration(self, step: str) -> Optional[int]:
        """
        조리 시간 추출 (분 단위)
        
        Args:
            step: 조리 단계 텍스트
            
        Returns:
            시간(분) 또는 None
        """
        patterns = [
            (r'(\d+)\s*분', 1),      # N분
            (r'(\d+)\s*시간', 60),   # N시간
            (r'(\d+)\s*초', 1/60),   # N초
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, step)
            if match:
                value = int(match.group(1))
                result = int(value * multiplier)
                return max(1, result)  # 최소 1분

        return None

    def _estimate_difficulty(self, recipe: Dict) -> str:
        """
        난이도 추정
        
        키워드 및 단계 수 기반으로 난이도를 추정합니다.
        """
        # 텍스트 기반 추정
        text = f"{recipe.get('title', '')} {' '.join(recipe.get('steps', []))}".lower()

        for difficulty, keywords in self.difficulty_keywords.items():
            if any(kw in text for kw in keywords):
                return difficulty

        # 단계 수 기반 추정
        step_count = len(recipe.get('steps', []))
        if step_count <= 5:
            return '쉬움'
        elif step_count <= 10:
            return '보통'
        else:
            return '어려움'

    def _estimate_cooking_time(self, recipe: Dict) -> Optional[int]:
        """
        총 조리 시간 추정 (분)
        
        각 단계의 시간을 합산하거나, 단계 수로 추정합니다.
        """
        total_time = 0
        steps = recipe.get('steps', [])

        # 각 단계에서 시간 추출
        for step in steps:
            step_text = step if isinstance(step, str) else str(step)
            duration = self._extract_duration(step_text)
            if duration:
                total_time += duration

        if total_time > 0:
            return total_time

        # 단계 수 기반 추정 (단계당 평균 5분)
        if steps:
            return len(steps) * 5

        return None

    def _extract_servings(self, recipe: Dict) -> Optional[int]:
        """인분 정보 추출"""
        text = f"{recipe.get('title', '')} {' '.join(recipe.get('ingredients', []))}"
        
        patterns = [r'(\d+)\s*인분', r'(\d+)\s*인용', r'(\d+)\s*serving']

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _calculate_statistics(self) -> None:
        """통계 계산"""
        if not self.processed_recipes:
            return

        categories = Counter(r['category'] for r in self.processed_recipes)
        difficulties = Counter(r['difficulty'] for r in self.processed_recipes)
        sources = Counter(r['source'] for r in self.processed_recipes)

        cooking_times = [
            r['cooking_time'] for r in self.processed_recipes 
            if r['cooking_time']
        ]
        step_counts = [len(r['steps']) for r in self.processed_recipes]
        ingredient_counts = [len(r['ingredients']) for r in self.processed_recipes]

        self.statistics = {
            'total_recipes': len(self.processed_recipes),
            'categories': dict(categories),
            'difficulties': dict(difficulties),
            'sources': dict(sources),
            'avg_cooking_time': sum(cooking_times) / len(cooking_times) if cooking_times else 0,
            'avg_steps': sum(step_counts) / len(step_counts) if step_counts else 0,
            'avg_ingredients': sum(ingredient_counts) / len(ingredient_counts) if ingredient_counts else 0,
            'min_steps': min(step_counts) if step_counts else 0,
            'max_steps': max(step_counts) if step_counts else 0,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """통계 반환"""
        if not self.statistics:
            self._calculate_statistics()
        return self.statistics

    def save_processed_data(self, filename: Optional[str] = None) -> None:
        """
        처리된 데이터 저장
        
        Args:
            filename: 저장 파일명 (None이면 자동 생성)
        """
        if not self.processed_recipes:
            logger.warning("저장할 처리된 레시피가 없습니다.")
            return

        if filename is None:
            filename = f"processed_recipes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_dir = Path('data/processed')
        output_dir.mkdir(parents=True, exist_ok=True)

        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'recipes': self.processed_recipes,
                'statistics': self.statistics,
                'processed_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"{len(self.processed_recipes)}개 레시피를 {filepath}에 저장")


class RecipeValidator:
    """레시피 데이터 유효성 검증기"""

    @staticmethod
    def validate(recipe: Dict) -> Tuple[bool, List[str]]:
        """
        레시피 유효성 검사
        
        Args:
            recipe: 검사할 레시피 데이터
            
        Returns:
            (유효 여부, 오류 메시지 목록)
        """
        errors = []

        # 필수 필드 검사
        if not recipe.get('title'):
            errors.append("제목이 없습니다")

        if not recipe.get('ingredients'):
            errors.append("재료가 없습니다")

        if not recipe.get('steps'):
            errors.append("조리 단계가 없습니다")

        # 데이터 품질 검사
        title = recipe.get('title', '')
        if len(title) < 2:
            errors.append("제목이 너무 짧습니다")
        if len(title) > 100:
            errors.append("제목이 너무 깁니다")

        ingredients = recipe.get('ingredients', [])
        if len(ingredients) < 2:
            errors.append("재료가 너무 적습니다")

        steps = recipe.get('steps', [])
        if len(steps) < 1:
            errors.append("조리 단계가 없습니다")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_batch(recipes: List[Dict]) -> Dict[str, Any]:
        """
        배치 유효성 검사
        
        Args:
            recipes: 검사할 레시피 목록
            
        Returns:
            검사 결과 통계
        """
        valid_count = 0
        invalid_count = 0
        error_summary = Counter()

        for recipe in recipes:
            is_valid, errors = RecipeValidator.validate(recipe)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                for error in errors:
                    error_summary[error] += 1

        return {
            'total': len(recipes),
            'valid': valid_count,
            'invalid': invalid_count,
            'validity_rate': valid_count / len(recipes) if recipes else 0,
            'error_summary': dict(error_summary)
        }