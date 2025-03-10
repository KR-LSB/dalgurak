from transformers import AutoTokenizer
from typing import Dict
import torch
import logging

logger = logging.getLogger(__name__)
class RecipeTokenizer:
    def __init__(self):
        # 토크나이저 초기화
        self.max_length = 512
        self.tokenizer = AutoTokenizer.from_pretrained(
            'klue/bert-base',
            model_max_length=self.max_length
        )
        
        # 특수 토큰 추가
        self._add_special_tokens()
        
        logger.info(f"Vocabulary size: {len(self.tokenizer)}")
    
    def _add_special_tokens(self):
        """레시피 관련 특수 토큰 추가"""
        special_tokens = {
            'additional_special_tokens': [
                '[TITLE]',      # 레시피 제목 구분
                '[INGREDIENTS]', # 재료 목록 시작
                '[STEPS]',      # 조리 단계 시작
                '[STEP]',       # 개별 조리 단계
                '[TIME]',       # 조리 시간
                '[DIFFICULTY]'  # 난이도
            ]
        }
        num_added_tokens = self.tokenizer.add_special_tokens(special_tokens)
        logger.info(f"Added {num_added_tokens} special tokens")
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """텍스트를 토큰 기준으로 자르기"""
        encoded = self.tokenizer.encode(
            text,
            add_special_tokens=True,
            max_length=max_length,
            truncation=True
        )
        return self.tokenizer.decode(encoded)
    
    def preprocess_recipe(self, recipe: Dict) -> Dict:  # 들여쓰기 수정!
        try:
            # 텍스트 구성
            title = recipe['title'][:100]  # 제목 길이 제한
            
            # 재료 정보 처리 (최대 10개 재료)
            ingredients = ' '.join(
                [ing['name'] for ing in recipe['ingredients'][:10]]
            )
            
            # 조리 단계 처리 (최대 10개 단계)
            steps = ' '.join(
                [step['description'] for step in recipe['steps'][:10]]
            )
            
            # 메타데이터 안전하게 처리
            metadata = recipe.get('metadata', {})
            
            # time 정보 안전하게 추출
            time_info = '정보 없음'
            if isinstance(metadata.get('time'), dict):
                time_info = metadata['time'].get('original', '정보 없음')
            
            # difficulty 정보 안전하게 추출
            difficulty_info = '정보 없음'
            if isinstance(metadata.get('difficulty'), dict):
                difficulty_info = metadata['difficulty'].get('original', '정보 없음')
            
            # 전체 텍스트 구성
            full_text = f"[TITLE] {title} [INGREDIENTS] {ingredients} [STEPS] {steps} [TIME] {time_info} [DIFFICULTY] {difficulty_info}"
            
            # 토큰화
            encoded = self.tokenizer(
                full_text,
                padding='max_length',
                truncation=True,
                max_length=self.max_length,
                return_tensors='pt'
            )
            
            return {
                'input_ids': encoded['input_ids'],
                'attention_mask': encoded['attention_mask'],
                'token_type_ids': encoded['token_type_ids']
            }
                
        except Exception as e:
            logger.error(f"Error preprocessing recipe: {str(e)}")
            logger.error(f"Recipe title: {recipe.get('title', 'Unknown')}")
            raise