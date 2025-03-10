import json
import os
from typing import Dict, Optional
from pathlib import Path

class RecipePatternDB:
    def __init__(self, patterns_file: str = 'recipe_patterns.json'):
        self.patterns_file = patterns_file
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> Dict:
        """패턴 데이터베이스 로드"""
        # data 디렉토리의 경로 생성
        data_dir = Path(__file__).parent.parent.parent / 'data'
        patterns_path = data_dir / self.patterns_file
        
        if patterns_path.exists():
            with open(patterns_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._create_default_patterns()
    
    def _create_default_patterns(self) -> Dict:
        """기본 패턴 데이터베이스 생성"""
        default_patterns = {
            "10000recipe.com": {
                "title": {
                    "selectors": ["div.view2_summary h3", "h3.view_title"],
                    "attribute": "text"
                },
                "ingredients": {
                    "container": "div.cont_ingre2",
                    "items": "dd",
                    "name": "span.name",
                    "amount": "span.amount"
                },
                "steps": {
                    "container": "div.view_step",
                    "items": "div.view_step_cont",
                    "description": "text"
                },
                "metadata": {
                    "time": {
                        "selector": "span.view2_summary_info2",
                        "attribute": "text"
                    },
                    "difficulty": {
                        "selector": "span.view2_summary_info3",
                        "attribute": "text"
                    },
                    "servings": {
                        "selector": "span.view2_summary_info1",
                        "attribute": "text"
                    }
                }
            },
            "terms.naver.com": {
                "title": {
                    "selectors": ["div.synopsis_area h2", "div.title_area h2"],
                    "attribute": "text"
                },
                "ingredients": {
                    "container": "div.content_area",
                    "items": "p.recipe_material",
                    "name": None,  # 네이버는 재료와 양이 텍스트로 혼합됨
                    "amount": None
                },
                "steps": {
                    "container": "div.content_area",
                    "items": "div.step_area ol li",
                    "description": "text"
                },
                "metadata": {
                    "time": {
                        "selector": "span.cooking_time",
                        "attribute": "text"
                    },
                    "difficulty": {
                        "selector": "span.nan_level",
                        "attribute": "text"
                    },
                    "servings": {
                        "selector": "span.serving",
                        "attribute": "text"
                    }
                }
            }
        }
        
        # data 디렉토리 생성 및 패턴 저장
        data_dir = Path(__file__).parent.parent.parent / 'data'
        data_dir.mkdir(exist_ok=True)
        self._save_patterns(default_patterns)
        return default_patterns
    
    def _save_patterns(self, patterns: Dict):
        """패턴 데이터베이스 저장"""
        data_dir = Path(__file__).parent.parent.parent / 'data'
        patterns_path = data_dir / self.patterns_file
        
        with open(patterns_path, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2)
    
    def get_pattern(self, domain: str) -> Optional[Dict]:
        """특정 도메인의 패턴 반환"""
        return self.patterns.get(domain)
    
    def add_pattern(self, domain: str, pattern: Dict):
        """새로운 사이트 패턴 추가"""
        self.patterns[domain] = pattern
        self._save_patterns(self.patterns)
        
    def update_pattern(self, domain: str, pattern: Dict):
        """기존 사이트 패턴 업데이트"""
        if domain in self.patterns:
            self.patterns[domain].update(pattern)
            self._save_patterns(self.patterns)
            
    def list_supported_sites(self) -> list:
        """지원하는 사이트 목록 반환"""
        return list(self.patterns.keys())
    
    def validate_pattern(self, pattern: Dict) -> bool:
        """패턴 구조 유효성 검증"""
        required_fields = ['title', 'ingredients', 'steps']
        return all(field in pattern for field in required_fields)