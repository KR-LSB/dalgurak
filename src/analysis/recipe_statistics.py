from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import json
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import seaborn as sns

@dataclass
class RecipeStats:
    """레시피 통계 데이터 클래스"""
    total_recipes: int = 0
    avg_ingredients: float = 0.0
    avg_steps: float = 0.0
    avg_cooking_time: float = 0.0
    difficulty_distribution: Dict[str, int] = None
    category_distribution: Dict[str, int] = None
    common_ingredients: Dict[str, int] = None
    time_distribution: Dict[str, int] = None
    missing_rates: Dict[str, float] = None

    def __post_init__(self):
        self.difficulty_distribution = {}
        self.category_distribution = {}
        self.common_ingredients = {}
        self.time_distribution = {}
        self.missing_rates = {}

class RecipeStatistics:
    """레시피 데이터 통계 분석 클래스"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.stats = RecipeStats()
        
    def _setup_logger(self):
        logger = logging.getLogger('RecipeStatistics')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            fh = logging.FileHandler('recipe_statistics.log')
            fh.setLevel(logging.INFO)
            
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            logger.addHandler(fh)
            logger.addHandler(ch)
        
        return logger

    def analyze_recipes(self, recipes: List[Dict]) -> RecipeStats:
        """레시피 데이터 분석"""
        try:
            self.logger.info(f"레시피 데이터 분석 시작: {len(recipes)}개 레시피")
            
            # 기본 통계
            self.stats.total_recipes = len(recipes)
            
            # 기본 메트릭 계산
            self._calculate_basic_metrics(recipes)
            
            # 분포 분석
            self._analyze_distributions(recipes)
            
            # 재료 분석
            self._analyze_ingredients(recipes)
            
            # 결측치 분석
            self._analyze_missing_values(recipes)
            
            self.logger.info("레시피 데이터 분석 완료")
            return self.stats
            
        except Exception as e:
            self.logger.error(f"데이터 분석 중 오류 발생: {str(e)}")
            raise

    def _calculate_basic_metrics(self, recipes: List[Dict]):
        """기본 메트릭 계산"""
        total_ingredients = 0
        total_steps = 0
        total_time = 0
        valid_time_count = 0
        
        for recipe in recipes:
            # 재료 수
            ingredients = recipe.get('ingredients', [])
            total_ingredients += len(ingredients)
            
            # 조리 단계 수
            steps = recipe.get('steps', [])
            total_steps += len(steps)
            
            # 조리 시간
            time_info = recipe.get('metadata', {}).get('time', {})
            minutes = time_info.get('minutes')
            if minutes and isinstance(minutes, (int, float)):
                total_time += minutes
                valid_time_count += 1
        
        # 평균 계산
        self.stats.avg_ingredients = round(total_ingredients / len(recipes), 2)
        self.stats.avg_steps = round(total_steps / len(recipes), 2)
        if valid_time_count > 0:
            self.stats.avg_cooking_time = round(total_time / valid_time_count, 2)

    def _analyze_distributions(self, recipes: List[Dict]):
        """분포 분석"""
        difficulty_counts = Counter()
        category_counts = Counter()
        time_ranges = {
            '~15분': 0,
            '16~30분': 0,
            '31~60분': 0,
            '1~2시간': 0,
            '2시간 이상': 0
        }
        
        for recipe in recipes:
            # 난이도 분포
            difficulty = recipe.get('metadata', {}).get('difficulty', {}).get('level')
            if difficulty:
                difficulty_label = {1: '초급', 2: '중급', 3: '고급'}.get(difficulty, '기타')
                difficulty_counts[difficulty_label] += 1
            
            # 카테고리 분포
            category = recipe.get('category', '기타')
            category_counts[category] += 1
            
            # 시간 분포
            minutes = recipe.get('metadata', {}).get('time', {}).get('minutes')
            if minutes:
                if minutes <= 15:
                    time_ranges['~15분'] += 1
                elif minutes <= 30:
                    time_ranges['16~30분'] += 1
                elif minutes <= 60:
                    time_ranges['31~60분'] += 1
                elif minutes <= 120:
                    time_ranges['1~2시간'] += 1
                else:
                    time_ranges['2시간 이상'] += 1
        
        self.stats.difficulty_distribution = dict(difficulty_counts)
        self.stats.category_distribution = dict(category_counts)
        self.stats.time_distribution = time_ranges

    def _analyze_ingredients(self, recipes: List[Dict]):
        """재료 분석"""
        ingredient_counts = Counter()
        
        for recipe in recipes:
            for ingredient in recipe.get('ingredients', []):
                name = ingredient.get('name', '').strip()
                if name:
                    ingredient_counts[name] += 1
        
        # 상위 50개 재료만 저장
        self.stats.common_ingredients = dict(ingredient_counts.most_common(50))

    def _analyze_missing_values(self, recipes: List[Dict]):
        """결측치 분석"""
        total = len(recipes)
        missing_counts = {
            '제목': 0,
            '재료': 0,
            '조리단계': 0,
            '조리시간': 0,
            '난이도': 0,
            '분량': 0
        }
        
        for recipe in recipes:
            # 제목 결측
            if not recipe.get('title'):
                missing_counts['제목'] += 1
            
            # 재료 결측
            if not recipe.get('ingredients'):
                missing_counts['재료'] += 1
            
            # 조리단계 결측
            if not recipe.get('steps'):
                missing_counts['조리단계'] += 1
            
            # 메타데이터 결측
            metadata = recipe.get('metadata', {})
            if not metadata.get('time', {}).get('minutes'):
                missing_counts['조리시간'] += 1
            if not metadata.get('difficulty', {}).get('level'):
                missing_counts['난이도'] += 1
            if not metadata.get('servings', {}).get('servings'):
                missing_counts['분량'] += 1
        
        # 결측률 계산
        self.stats.missing_rates = {
            field: round(count / total * 100, 2)
            for field, count in missing_counts.items()
        }

    def generate_reports(self, output_dir: Path = None):
        """통계 리포트 생성"""
        if output_dir is None:
            output_dir = Path('data/reports')
        
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 통계 저장
        stats_file = output_dir / f'recipe_statistics_{timestamp}.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.stats), f, ensure_ascii=False, indent=2)
        
        # 텍스트 리포트 생성
        report_file = output_dir / f'recipe_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== 레시피 데이터 분석 리포트 ===\n\n")
            
            f.write("1. 기본 통계\n")
            f.write(f"- 전체 레시피 수: {self.stats.total_recipes:,}개\n")
            f.write(f"- 평균 재료 수: {self.stats.avg_ingredients:.1f}개\n")
            f.write(f"- 평균 조리 단계: {self.stats.avg_steps:.1f}단계\n")
            f.write(f"- 평균 조리 시간: {self.stats.avg_cooking_time:.1f}분\n\n")
            
            f.write("2. 난이도 분포\n")
            for level, count in self.stats.difficulty_distribution.items():
                f.write(f"- {level}: {count:,}개 ({count/self.stats.total_recipes*100:.1f}%)\n")
            f.write("\n")
            
            f.write("3. 조리시간 분포\n")
            for time_range, count in self.stats.time_distribution.items():
                f.write(f"- {time_range}: {count:,}개 ({count/self.stats.total_recipes*100:.1f}%)\n")
            f.write("\n")
            
            f.write("4. 자주 사용되는 재료 (상위 10개)\n")
            for name, count in list(self.stats.common_ingredients.items())[:10]:
                f.write(f"- {name}: {count:,}회\n")
            f.write("\n")
            
            f.write("5. 결측치 비율\n")
            for field, rate in self.stats.missing_rates.items():
                f.write(f"- {field}: {rate:.1f}%\n")
        
        self.logger.info(f"통계 리포트가 생성되었습니다:")
        self.logger.info(f"- JSON 통계: {stats_file}")
        self.logger.info(f"- 텍스트 리포트: {report_file}")

    def generate_visualizations(self, output_dir: Path = None):
        """시각화 생성"""
        if output_dir is None:
            output_dir = Path('data/visualizations')
        
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        plt.style.use('seaborn')
        
        # 1. 난이도 분포 파이 차트
        plt.figure(figsize=(10, 6))
        plt.pie(
            self.stats.difficulty_distribution.values(),
            labels=self.stats.difficulty_distribution.keys(),
            autopct='%1.1f%%'
        )
        plt.title('레시피 난이도 분포')
        plt.savefig(output_dir / f'difficulty_distribution_{timestamp}.png')
        plt.close()
        
        # 2. 조리시간 분포 막대 그래프
        plt.figure(figsize=(12, 6))
        times = list(self.stats.time_distribution.keys())
        counts = list(self.stats.time_distribution.values())
        plt.bar(times, counts)
        plt.title('조리시간 분포')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / f'cooking_time_distribution_{timestamp}.png')
        plt.close()
        
        # 3. 상위 20개 재료 막대 그래프
        plt.figure(figsize=(15, 8))
        ingredients = list(self.stats.common_ingredients.keys())[:20]
        counts = list(self.stats.common_ingredients.values())[:20]
        plt.barh(ingredients, counts)
        plt.title('자주 사용되는 재료 (상위 20개)')
        plt.tight_layout()
        plt.savefig(output_dir / f'common_ingredients_{timestamp}.png')
        plt.close()
        
        # 4. 결측치 비율 막대 그래프
        plt.figure(figsize=(10, 6))
        fields = list(self.stats.missing_rates.keys())
        rates = list(self.stats.missing_rates.values())
        plt.bar(fields, rates)
        plt.title('필드별 결측치 비율')
        plt.xticks(rotation=45)
        plt.ylabel('결측률 (%)')
        plt.tight_layout()
        plt.savefig(output_dir / f'missing_rates_{timestamp}.png')
        plt.close()
        
        self.logger.info(f"시각화 파일이 {output_dir}에 생성되었습니다.")