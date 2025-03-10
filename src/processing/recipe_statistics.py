# src/processing/recipe_statistics.py
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import json
import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns

class RecipeStatistics:
    def __init__(self):
        self.logger = self._setup_logger()
        self.stats = {
            'total_recipes': 0,
            'category_stats': {},
            'ingredient_stats': {},
            'step_stats': {},
            'time_stats': {},
            'analyzed_at': datetime.now().isoformat()
        }

    def _setup_logger(self):
        logger = logging.getLogger('RecipeStatistics')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            fh = logging.FileHandler('recipe_statistics.log')
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            logger.addHandler(fh)
            logger.addHandler(ch)
        
        return logger

    def analyze_recipes(self, recipes: List[Dict]) -> Dict:
        """레시피 데이터 분석"""
        self.logger.info(f"총 {len(recipes)}개 레시피 분석 시작")
        self.stats['total_recipes'] = len(recipes)

        # 1. 카테고리 분석
        self._analyze_categories(recipes)
        
        # 2. 재료 분석
        self._analyze_ingredients(recipes)
        
        # 3. 조리 단계 분석
        self._analyze_steps(recipes)
        
        # 4. 조리 시간 분석
        self._analyze_cooking_time(recipes)

        return self.stats

    def _analyze_categories(self, recipes: List[Dict]):
        """카테고리 분석"""
        categories = [recipe.get('category', '기타') for recipe in recipes]
        category_counts = Counter(categories)
        
        self.stats['category_stats'] = {
            'distribution': dict(category_counts),
            'total_categories': len(category_counts),
            'top_categories': dict(category_counts.most_common(10))
        }

    def _analyze_ingredients(self, recipes: List[Dict]):
        """재료 분석"""
        all_ingredients = []
        ingredient_counts = []
        
        for recipe in recipes:
            ingredients = recipe.get('ingredients', [])
            ingredient_counts.append(len(ingredients))
            
            for ingredient in ingredients:
                name = ingredient.get('name', '')
                if name:
                    all_ingredients.append(name)
        
        ingredient_freq = Counter(all_ingredients)
        
        self.stats['ingredient_stats'] = {
            'avg_ingredients_per_recipe': round(sum(ingredient_counts) / len(recipes), 2),
            'min_ingredients': min(ingredient_counts),
            'max_ingredients': max(ingredient_counts),
            'most_common_ingredients': dict(ingredient_freq.most_common(20)),
            'total_unique_ingredients': len(ingredient_freq)
        }

    def _analyze_steps(self, recipes: List[Dict]):
        """조리 단계 분석"""
        step_counts = []
        step_lengths = []
        
        for recipe in recipes:
            steps = recipe.get('steps', [])
            step_counts.append(len(steps))
            
            for step in steps:
                description = step.get('description', '')
                step_lengths.append(len(description))
        
        self.stats['step_stats'] = {
            'avg_steps_per_recipe': round(sum(step_counts) / len(recipes), 2),
            'min_steps': min(step_counts),
            'max_steps': max(step_counts),
            'avg_step_length': round(sum(step_lengths) / len(step_lengths), 2) if step_lengths else 0,
            'step_count_distribution': {
                '1-5': len([x for x in step_counts if 1 <= x <= 5]),
                '6-10': len([x for x in step_counts if 6 <= x <= 10]),
                '11-15': len([x for x in step_counts if 11 <= x <= 15]),
                '16+': len([x for x in step_counts if x >= 16])
            }
        }

    def _analyze_cooking_time(self, recipes: List[Dict]):
        """조리 시간 분석"""
        cooking_times = []
        
        for recipe in recipes:
            time_info = recipe.get('metadata', {}).get('time', {})
            minutes = time_info.get('minutes')
            if minutes is not None:
                cooking_times.append(minutes)
        
        if cooking_times:
            self.stats['time_stats'] = {
                'avg_cooking_time': round(sum(cooking_times) / len(cooking_times), 2),
                'min_cooking_time': min(cooking_times),
                'max_cooking_time': max(cooking_times),
                'time_distribution': {
                    '~15분': len([x for x in cooking_times if x <= 15]),
                    '16-30분': len([x for x in cooking_times if 15 < x <= 30]),
                    '31-60분': len([x for x in cooking_times if 30 < x <= 60]),
                    '1-2시간': len([x for x in cooking_times if 60 < x <= 120]),
                    '2시간+': len([x for x in cooking_times if x > 120])
                }
            }

    def generate_visualizations(self, output_dir: Path = None):
        """시각화 생성"""
        if output_dir is None:
            output_dir = Path('data/statistics/visualizations')
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. 카테고리 분포
        plt.figure(figsize=(12, 6))
        categories = self.stats['category_stats']['top_categories']
        plt.bar(categories.keys(), categories.values())
        plt.title('상위 10개 레시피 카테고리')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / 'category_distribution.png')
        plt.close()

        # 2. 재료 분포
        plt.figure(figsize=(12, 6))
        ingredients = dict(list(self.stats['ingredient_stats']['most_common_ingredients'].items())[:15])
        plt.bar(ingredients.keys(), ingredients.values())
        plt.title('가장 많이 사용되는 재료 Top 15')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / 'ingredient_distribution.png')
        plt.close()

        # 3. 조리 시간 분포
        plt.figure(figsize=(10, 6))
        time_dist = self.stats['time_stats']['time_distribution']
        plt.pie(time_dist.values(), labels=time_dist.keys(), autopct='%1.1f%%')
        plt.title('조리 시간 분포')
        plt.savefig(output_dir / 'cooking_time_distribution.png')
        plt.close()

    def save_statistics(self, output_dir: Path = None):
        """통계 결과 저장"""
        if output_dir is None:
            output_dir = Path('data/statistics')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 형식으로 저장
        stats_file = output_dir / f'recipe_statistics_{timestamp}.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        # 텍스트 리포트 생성
        report_file = output_dir / f'recipe_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== 레시피 데이터 분석 리포트 ===\n\n")
            
            f.write(f"1. 기본 통계\n")
            f.write(f"- 전체 레시피 수: {self.stats['total_recipes']:,}개\n")
            f.write(f"- 카테고리 수: {self.stats['category_stats']['total_categories']}개\n")
            f.write(f"- 고유 재료 수: {self.stats['ingredient_stats']['total_unique_ingredients']:,}개\n\n")
            
            f.write(f"2. 재료 통계\n")
            f.write(f"- 레시피당 평균 재료 수: {self.stats['ingredient_stats']['avg_ingredients_per_recipe']}개\n")
            f.write(f"- 최소 재료 수: {self.stats['ingredient_stats']['min_ingredients']}개\n")
            f.write(f"- 최대 재료 수: {self.stats['ingredient_stats']['max_ingredients']}개\n\n")
            
            f.write(f"3. 조리 단계 통계\n")
            f.write(f"- 레시피당 평균 단계 수: {self.stats['step_stats']['avg_steps_per_recipe']}단계\n")
            f.write(f"- 최소 단계 수: {self.stats['step_stats']['min_steps']}단계\n")
            f.write(f"- 최대 단계 수: {self.stats['step_stats']['max_steps']}단계\n")
            f.write(f"- 평균 설명 길이: {self.stats['step_stats']['avg_step_length']}자\n\n")
            
            f.write(f"4. 조리 시간 통계\n")
            f.write(f"- 평균 조리 시간: {self.stats['time_stats']['avg_cooking_time']}분\n")
            f.write(f"- 최소 조리 시간: {self.stats['time_stats']['min_cooking_time']}분\n")
            f.write(f"- 최대 조리 시간: {self.stats['time_stats']['max_cooking_time']}분\n")
        
        self.logger.info(f"통계 결과를 저장했습니다:")
        self.logger.info(f"- JSON 통계: {stats_file}")
        self.logger.info(f"- 텍스트 리포트: {report_file}")