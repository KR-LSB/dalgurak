import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import re

class RecipeValidator:
    def __init__(self):
        self.logger = self._setup_logger()
        self.reset_validation_results()

    def _setup_logger(self):
        logger = logging.getLogger('RecipeValidator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 파일 핸들러
            fh = logging.FileHandler('recipe_validation.log')
            fh.setLevel(logging.INFO)
            
            # 콘솔 핸들러
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            # 포맷터
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            logger.addHandler(fh)
            logger.addHandler(ch)
        
        return logger

    def reset_validation_results(self):
        """검증 결과 초기화"""
        self.validation_results = {
            'total_recipes': 0,
            'valid_recipes': 0,
            'invalid_recipes': 0,
            'issues': [],
            'validation_date': datetime.now().isoformat(),
            'issue_summary': {}
        }

    def validate_recipe(self, recipe: Dict) -> Tuple[bool, List[str]]:
        """개별 레시피 검증"""
        issues = []

        # 1. 필수 필드 존재 여부 검증
        required_fields = ['_id', 'title', 'ingredients', 'steps', 'url']
        for field in required_fields:
            if field not in recipe:
                issues.append(f"필수 필드 누락: {field}")

        # 2. 제목 검증
        if 'title' in recipe and recipe['title']:
            title_issues = self._validate_title(recipe['title'])
            issues.extend(title_issues)

        # 3. 재료 검증
        if 'ingredients' in recipe and recipe['ingredients']:
            ingredient_issues = self._validate_ingredients(recipe['ingredients'])
            issues.extend(ingredient_issues)

        # 4. 조리 단계 검증
        if 'steps' in recipe and recipe['steps']:
            step_issues = self._validate_steps(recipe['steps'])
            issues.extend(step_issues)

        return len(issues) == 0, issues

    def _validate_title(self, title: str) -> List[str]:
        """제목 검증"""
        issues = []
        
        if not isinstance(title, str):
            issues.append("제목이 문자열이 아님")
            return issues

        if len(title.strip()) < 2:
            issues.append("제목이 너무 짧음 (최소 2자)")
        elif len(title) > 200:
            issues.append("제목이 너무 김 (최대 200자)")

        return issues

    def _validate_ingredients(self, ingredients: List) -> List[str]:
        """재료 검증"""
        issues = []
        
        if not isinstance(ingredients, list):
            issues.append("재료 정보가 리스트 형식이 아님")
            return issues

        if not ingredients:
            issues.append("재료 목록이 비어있음")
            return issues

        for idx, ingredient in enumerate(ingredients):
            if not isinstance(ingredient, dict):
                issues.append(f"재료 {idx+1}번: 잘못된 형식")
                continue

            # 재료명 검증
            name = ingredient.get('name', '')
            if not name or len(name.strip()) < 1:
                issues.append(f"재료 {idx+1}번: 재료명 누락")

            # 수량 검증
            amount = ingredient.get('amount', {})
            if amount:
                if not isinstance(amount, dict):
                    issues.append(f"재료 {idx+1}번: 잘못된 수량 형식")
                else:
                    if 'value' in amount and amount['value'] is not None:
                        if not isinstance(amount['value'], (int, float)):
                            issues.append(f"재료 {idx+1}번: 잘못된 수량 값 형식")

        return issues

    def _validate_steps(self, steps: List) -> List[str]:
        """조리 단계 검증"""
        issues = []
        
        if not isinstance(steps, list):
            issues.append("조리 단계가 리스트 형식이 아님")
            return issues

        if not steps:
            issues.append("조리 단계가 비어있음")
            return issues

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                issues.append(f"단계 {idx+1}번: 잘못된 형식")
                continue

            # 단계 번호 검증
            step_num = step.get('step_num')
            if step_num is None:
                issues.append(f"단계 {idx+1}번: 번호 누락")
            elif not isinstance(step_num, int):
                issues.append(f"단계 {idx+1}번: 잘못된 번호 형식")

            # 설명 검증
            description = step.get('description', '')
            if not description or len(description.strip()) < 5:
                issues.append(f"단계 {idx+1}번: 설명 누락 또는 너무 짧음")

        return issues

    def validate_recipes(self, recipes: List[Dict]) -> Dict:
        """전체 레시피 검증"""
        self.reset_validation_results()
        self.validation_results['total_recipes'] = len(recipes)

        for idx, recipe in enumerate(recipes, 1):
            try:
                is_valid, issues = self.validate_recipe(recipe)
                
                if is_valid:
                    self.validation_results['valid_recipes'] += 1
                else:
                    self.validation_results['invalid_recipes'] += 1
                    self.validation_results['issues'].append({
                        'recipe_id': recipe.get('_id', f'recipe_{idx}'),
                        'issues': issues
                    })

                    # 이슈 유형 집계
                    for issue in issues:
                        self.validation_results['issue_summary'][issue] = \
                            self.validation_results['issue_summary'].get(issue, 0) + 1

                if idx % 100 == 0:
                    self.logger.info(f"{idx}/{len(recipes)} 레시피 검증 완료")

            except Exception as e:
                self.logger.error(f"레시피 검증 실패 (ID: {recipe.get('_id', 'unknown')}): {str(e)}")
                continue

        self.logger.info(f"검증 완료: "
                        f"전체 {self.validation_results['total_recipes']}, "
                        f"유효 {self.validation_results['valid_recipes']}, "
                        f"유효하지 않음 {self.validation_results['invalid_recipes']}")

        return self.validation_results

    def save_validation_results(self, output_dir: Path = None):
        """검증 결과 저장"""
        if output_dir is None:
            output_dir = Path('data/validation')
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'validation_results_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"검증 결과를 {output_file}에 저장했습니다.")

        # 요약 정보 출력
        print("\n=== 검증 결과 요약 ===")
        print(f"전체 레시피: {self.validation_results['total_recipes']}")
        print(f"유효한 레시피: {self.validation_results['valid_recipes']}")
        print(f"유효하지 않은 레시피: {self.validation_results['invalid_recipes']}")
        
        if self.validation_results['issue_summary']:
            print("\n주요 이슈:")
            for issue, count in sorted(self.validation_results['issue_summary'].items(), 
                                    key=lambda x: x[1], reverse=True):
                print(f"- {issue}: {count}건")