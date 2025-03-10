import torch
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from sklearn.model_selection import train_test_split
from transformers import AutoConfig
from safetensors.torch import load_file

from model import RecipeBERTModel
from tokenizer import RecipeTokenizer
from trainer import RecipeDataset
from torch.utils.data import DataLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_recipes_from_mongodb():
    """MongoDB에서 레시피 데이터 로드"""
    try:
        load_dotenv()
        username = os.getenv('MONGODB_USERNAME')
        password = os.getenv('MONGODB_PASSWORD')
        cluster = os.getenv('MONGODB_CLUSTER')
        
        uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=lsb"
        client = MongoClient(uri)
        db = client['recipe_db']
        
        recipes = list(db.recipes.find({}, {'_id': 0}))
        logger.info(f"MongoDB에서 {len(recipes)}개의 레시피를 로드했습니다.")
        
        return recipes
        
    except Exception as e:
        logger.error(f"MongoDB에서 데이터 로드 중 오류 발생: {e}")
        raise

# ... [이전 imports 유지]

class MetricsEvaluator:
    def __init__(self, model_path: str, test_dataset: RecipeDataset):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = RecipeTokenizer()
        
        # config와 모델 로드
        logger.info("모델 설정 및 가중치 로드 중...")
        try:
            # config 로드
            config = AutoConfig.from_pretrained(model_path)
            config.vocab_size = len(self.tokenizer.tokenizer)
            
            # 모델 초기화
            self.model = RecipeBERTModel(config)
            
            # safetensors 파일에서 가중치 로드
            state_dict = load_file(Path(model_path) / 'model.safetensors')
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            logger.info("모델 로드 완료")
            
        except Exception as e:
            logger.error(f"모델 로드 중 오류 발생: {e}")
            raise
        
        self.test_loader = DataLoader(
            test_dataset,
            batch_size=32,
            shuffle=False,
            num_workers=0
        )
        
        self.categories = [
            '과자', '국/탕', '기타', '김치/젓갈/장류', '디저트', '메인반찬', 
            '면/만두', '밑반찬', '밥/죽/떡', '빵', '샐러드', '스프', 
            '양념/소스/잼', '양식', '찌개', '차/음료/술', '퓨전'
        ]
        
    def evaluate(self):
        """전체 평가 실행"""
        true_categories = []
        pred_categories = []
        true_difficulties = []
        pred_difficulties = []
        true_times = []
        pred_times = []
        
        with torch.no_grad():
            for batch in self.test_loader:
                # 데이터를 GPU로 이동
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else 
                        {k2: v2.to(self.device) for k2, v2 in v.items()} 
                        for k, v in batch.items()}
                
                outputs = self.model(
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask'],
                    token_type_ids=batch['token_type_ids']
                )
                
                # 예측값 계산
                cat_preds = torch.argmax(outputs['category_logits'], dim=1)
                diff_preds = torch.argmax(outputs['difficulty_logits'], dim=1)
                time_preds = torch.argmax(outputs['time_logits'], dim=1)
                
                # CPU로 이동 및 리스트에 추가
                true_categories.extend(batch['labels']['category'].cpu().numpy())
                pred_categories.extend(cat_preds.cpu().numpy())
                true_difficulties.extend(batch['labels']['difficulty'].cpu().numpy())
                pred_difficulties.extend(diff_preds.cpu().numpy())
                true_times.extend(batch['labels']['time'].cpu().numpy())
                pred_times.extend(time_preds.cpu().numpy())
        
        # 디버깅: 예측값과 실제값의 범위 확인
        logger.info(f"카테고리 예측값 범위: {min(pred_categories)} ~ {max(pred_categories)}")
        logger.info(f"카테고리 실제값 범위: {min(true_categories)} ~ {max(true_categories)}")
        logger.info(f"Unique predicted categories: {sorted(set(pred_categories))}")
        logger.info(f"Unique true categories: {sorted(set(true_categories))}")
        
        # 결과 평가
        results = {
            'category': self._evaluate_task(true_categories, pred_categories, self.categories, 'Category', add_labels_info=True),
            'difficulty': self._evaluate_task(true_difficulties, pred_difficulties, ['쉬움', '보통', '어려움'], 'Difficulty'),
            'time': self._evaluate_task(true_times, pred_times, ['30분미만', '30-60분', '60분이상'], 'Cooking Time')
        }
        
        return results
    
    def _evaluate_task(self, y_true: List, y_pred: List, labels: List, task_name: str, add_labels_info: bool = False) -> Dict:
        """각 태스크별 평가"""
        if add_labels_info:
            # 라벨 정보 출력
            logger.info(f"\n{task_name} Labels Info:")
            logger.info(f"Labels provided: {labels}")
            logger.info(f"Unique values in y_true: {sorted(set(y_true))}")
            logger.info(f"Unique values in y_pred: {sorted(set(y_pred))}")
        
        # 라벨 범위 조정
        unique_labels = sorted(list(set(y_true)))
        label_map = {old_idx: new_idx for new_idx, old_idx in enumerate(unique_labels)}
        y_true_mapped = [label_map[y] for y in y_true]
        y_pred_mapped = [label_map[y] for y in y_pred]
        
        # 실제 사용된 라벨만 선택
        used_labels = [labels[i] for i in unique_labels]
        
        # 기본 메트릭스
        accuracy = accuracy_score(y_true_mapped, y_pred_mapped)
        report = classification_report(y_true_mapped, y_pred_mapped, 
                                    target_names=used_labels, output_dict=True)
        conf_matrix = confusion_matrix(y_true_mapped, y_pred_mapped)
        
        # 혼동 행렬 시각화
        plt.figure(figsize=(12, 8))
        sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues',
                   xticklabels=used_labels, yticklabels=used_labels)
        plt.title(f'Confusion Matrix - {task_name}')
        plt.xlabel('Predicted')
        plt.ylabel('True')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=45)
        plt.tight_layout()
        
        # 결과 저장
        save_dir = Path('evaluation_results')
        save_dir.mkdir(exist_ok=True)
        plt.savefig(save_dir / f'confusion_matrix_{task_name.lower()}.png', 
                   bbox_inches='tight', dpi=300)
        plt.close()
        
        return {
            'accuracy': accuracy,
            'classification_report': report,
            'confusion_matrix': conf_matrix.tolist()
        }

# ... [main 함수는 그대로 유지]
    
    def print_results(self, results: Dict):
        """결과 출력"""
        for task_name, task_results in results.items():
            print(f"\n=== {task_name.upper()} CLASSIFICATION RESULTS ===")
            print(f"Accuracy: {task_results['accuracy']:.4f}")
            
            # 분류 리포트 출력
            report = task_results['classification_report']
            print("\nDetailed metrics per class:")
            print("-" * 90)
            print(f"{'Class':<25} {'Precision':>12} {'Recall':>12} {'F1-score':>12} {'Support':>12}")
            print("-" * 90)
            
            for label, metrics in report.items():
                if isinstance(metrics, dict):
                    print(f"{label:<25} {metrics['precision']:>12.4f} {metrics['recall']:>12.4f} "
                          f"{metrics['f1-score']:>12.4f} {metrics['support']:>12}")
            print("-" * 90)
            print(f"\nMacro Avg: {report['macro avg']['f1-score']:.4f}")
            print(f"Weighted Avg: {report['weighted avg']['f1-score']:.4f}")

def main():
    # 모델 경로 설정
    model_path = "models/recipe_bert_20250109_202940"
    
    # 데이터 로드 및 분할
    logger.info("데이터 로드 중...")
    recipes = load_recipes_from_mongodb()
    
    # 데이터 분할
    _, temp_recipes = train_test_split(recipes, test_size=0.2, random_state=42)
    _, test_recipes = train_test_split(temp_recipes, test_size=0.5, random_state=42)
    
    # 토크나이저 및 테스트 데이터셋 생성
    tokenizer = RecipeTokenizer()
    test_dataset = RecipeDataset(test_recipes, tokenizer)
    
    # 평가 실행
    logger.info("성능 평가 시작...")
    evaluator = MetricsEvaluator(model_path, test_dataset)
    results = evaluator.evaluate()
    evaluator.print_results(results)
    logger.info("평가 완료! evaluation_results 디렉토리에서 혼동 행렬을 확인하세요.")

if __name__ == '__main__':
    main()