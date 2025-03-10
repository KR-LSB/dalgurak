import torch
from torch.utils.data import Dataset, DataLoader
from transformers import get_linear_schedule_with_warmup
from typing import Dict, List
import numpy as np
from tqdm import tqdm
import logging
from pathlib import Path
import json

from model import RecipeBERTModel
from tokenizer import RecipeTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecipeDataset(Dataset):
    def __init__(self, recipes: List[Dict], tokenizer: RecipeTokenizer):
        self.recipes = recipes
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.recipes)

    def __getitem__(self, idx):
        recipe = self.recipes[idx]
        
        # 텍스트 데이터 토큰화
        encoded = self.tokenizer.preprocess_recipe(recipe)
        
        # 레이블 준비 (안전하게 처리)
        metadata = recipe.get('metadata', {})
        labels = {
            'category': torch.tensor(self._get_category_label(recipe.get('category', '기타'))),
            'difficulty': torch.tensor(self._get_difficulty_label(metadata.get('difficulty', {}))),
            'time': torch.tensor(self._get_time_label(metadata.get('time', {})))
        }
        
        return {
            'input_ids': encoded['input_ids'].squeeze(),
            'attention_mask': encoded['attention_mask'].squeeze(),
            'token_type_ids': encoded['token_type_ids'].squeeze(),
            'labels': labels
        }

    def _get_difficulty_label(self, difficulty: Dict) -> int:
        """난이도 레이블 반환 (없는 경우 기본값 0)"""
        if not isinstance(difficulty, dict):
            return 0
        level = difficulty.get('level')
        if level is None:
            return 0
        return min(max(level - 1, 0), 2)

    def _get_time_label(self, time: Dict) -> int:
        """시간 레이블 반환 (없는 경우 기본값 0)"""
        if not isinstance(time, dict):
            return 0
        minutes = time.get('minutes')
        if minutes is None:
            return 0
        if minutes < 30:
            return 0
        elif minutes < 60:
            return 1
        else:
            return 2
    
    def _get_category_label(self, category: str) -> int:
        category_mapping = {
            '장아찌/김치/젓갈': '김치/젓갈/장류',
            '반찬': '메인반찬',
            '국/탕/찌개': '국/탕'
            # 다른 매핑이 필요한 경우 여기에 추가
        }
        
        # 카테고리 매핑 적용
        mapped_category = category_mapping.get(category, category)
        
        categories = [
            '과자', '국/탕', '기타', '김치/젓갈/장류', '디저트', '메인반찬', 
            '면/만두', '밑반찬', '밥/죽/떡', '빵', '샐러드', '스프', 
            '양념/소스/잼', '양식', '찌개', '차/음료/술', '퓨전'
        ]
        
        try:
            return categories.index(mapped_category)
        except ValueError:
            print(f"Unknown category: {category} (mapped to: {mapped_category})")
            return categories.index('기타')  # 알 수 없는 카테고리는 '기타'로 처리
        
    def _get_difficulty_label(self, difficulty: Dict) -> int:
        level = difficulty.get('level')
        if level is None:
            return 0
        return min(max(level - 1, 0), 2)
    
    def _get_time_label(self, time: Dict) -> int:
        minutes = time.get('minutes')
        if minutes is None:
            return 0
            
        if minutes < 30:
            return 0
        elif minutes < 60:
            return 1
        else:
            return 2

def collate_fn(batch):
    """커스텀 배치 생성 함수"""
    # 배치의 최대 길이 계산
    max_length = 512
    
    # 배치 텐서 초기화
    batch_size = len(batch)
    
    # 입력 데이터 처리
    input_ids = torch.stack([item['input_ids'][:max_length] for item in batch])
    attention_mask = torch.stack([item['attention_mask'][:max_length] for item in batch])
    token_type_ids = torch.stack([item['token_type_ids'][:max_length] for item in batch])
    
    # 레이블 처리
    category_labels = torch.stack([item['labels']['category'] for item in batch])
    difficulty_labels = torch.stack([item['labels']['difficulty'] for item in batch])
    time_labels = torch.stack([item['labels']['time'] for item in batch])
    
    return {
        'input_ids': input_ids,
        'attention_mask': attention_mask,
        'token_type_ids': token_type_ids,
        'labels': {
            'category': category_labels,
            'difficulty': difficulty_labels,
            'time': time_labels
        }
    }

class RecipeTrainer:
    def __init__(
        self,
        model: RecipeBERTModel,
        tokenizer: RecipeTokenizer,
        train_dataset: RecipeDataset,
        val_dataset: RecipeDataset,
        training_params: dict,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        output_dir: str = './models'
    ):
        self.model = model.to(device)
        self.tokenizer = tokenizer
        self.device = device
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 데이터로더 설정
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=training_params['batch_size'],
            shuffle=True,
            num_workers=2,
            collate_fn=collate_fn
        )
        
        self.val_loader = DataLoader(
            val_dataset,
            batch_size=training_params['batch_size'] * 2,
            shuffle=False,
            num_workers=2,
            collate_fn=collate_fn
        )
        
        # 옵티마이저 설정
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=2e-5,
            weight_decay=0.01
        )
        
        # 학습 스케줄러 설정
        num_training_steps = len(self.train_loader) * 3
        num_warmup_steps = num_training_steps // 10
        
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=num_warmup_steps,
            num_training_steps=num_training_steps
        )
    
    def train(self, num_epochs: int = 3):
        best_val_loss = float('inf')
        train_loss = 0
        
        for epoch in range(num_epochs):
            logger.info(f"Epoch {epoch + 1}/{num_epochs}")
            
            # 학습
            self.model.train()
            epoch_loss = 0
            train_steps = 0
            
            progress_bar = tqdm(self.train_loader, desc=f"Training epoch {epoch + 1}")
            for batch in progress_bar:
                self.optimizer.zero_grad()
                
                # 데이터를 GPU로 이동
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else 
                        {k2: v2.to(self.device) for k2, v2 in v.items()} 
                        for k, v in batch.items()}
                
                # 모델 출력
                outputs = self.model(
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask'],
                    token_type_ids=batch['token_type_ids'],
                    labels=batch['labels']
                )
                
                loss = outputs['loss']
                loss.backward()
                
                self.optimizer.step()
                self.scheduler.step()
                
                epoch_loss += loss.item()
                train_steps += 1
                train_loss = epoch_loss / train_steps
                
                # 진행 상황 업데이트
                progress_bar.set_postfix({
                    'loss': f"{train_loss:.4f}"
                })
            
            logger.info(f"Average training loss: {train_loss:.4f}")
            
            # 검증
            val_loss = self.evaluate()
            logger.info(f"Validation loss: {val_loss:.4f}")
            
            # 모델 저장
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_model()
        
        return train_loss
    
    def evaluate(self):
        self.model.eval()
        val_loss = 0
        val_steps = 0
        
        with torch.no_grad():
            for batch in tqdm(self.val_loader, desc="Evaluating"):
                # 데이터를 GPU로 이동
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else 
                        {k2: v2.to(self.device) for k2, v2 in v.items()} 
                        for k, v in batch.items()}
                
                outputs = self.model(
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask'],
                    token_type_ids=batch['token_type_ids'],
                    labels=batch['labels']
                )
                
                val_loss += outputs['loss'].item()
                val_steps += 1
        
        return val_loss / val_steps
    
    def save_model(self):
        # 모델 저장
        self.model.save_pretrained(self.output_dir)
        self.tokenizer.tokenizer.save_pretrained(self.output_dir)
        logger.info(f"Model saved to {self.output_dir}")