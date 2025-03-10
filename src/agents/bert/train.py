import json
from pathlib import Path
import torch
from transformers import AutoConfig
import logging
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from model import RecipeBERTModel
from tokenizer import RecipeTokenizer
from trainer import RecipeDataset, RecipeTrainer
from db_logger import ModelLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_recipes_from_mongodb():
    """MongoDB에서 레시피 데이터 로드"""
    try:
        # MongoDB 연결 설정
        load_dotenv()
        username = os.getenv('MONGODB_USERNAME')
        password = os.getenv('MONGODB_PASSWORD')
        cluster = os.getenv('MONGODB_CLUSTER')
        
        uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=lsb"
        client = MongoClient(uri)
        db = client['recipe_db']
        
        # 레시피 컬렉션에서 데이터 가져오기
        recipes = list(db.recipes.find({}, {'_id': 0}))  # _id 필드 제외
        logger.info(f"MongoDB에서 {len(recipes)}개의 레시피를 로드했습니다.")
        
        return recipes
        
    except Exception as e:
        logger.error(f"MongoDB에서 데이터 로드 중 오류 발생: {e}")
        raise

def main():
    # MongoDB 로거 초기화
    db_logger = ModelLogger()
    model_version = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # MongoDB에서 데이터 로드
    logger.info("MongoDB에서 레시피 데이터 로드 중...")
    recipes = load_recipes_from_mongodb()
    logger.info(f"총 {len(recipes)}개의 레시피를 로드했습니다.")
    
    # 데이터 분할 (train: 80%, val: 10%, test: 10%)
    from sklearn.model_selection import train_test_split
    train_recipes, temp_recipes = train_test_split(recipes, test_size=0.2, random_state=42)
    val_recipes, test_recipes = train_test_split(temp_recipes, test_size=0.5, random_state=42)
    
    logger.info(f"데이터 분할 - Train: {len(train_recipes)}, Val: {len(val_recipes)}, Test: {len(test_recipes)}")
    
    # 학습 파라미터 설정
    training_params = {
        'num_epochs': 3,
        'batch_size': 8,
        'learning_rate': 5e-5,
        'weight_decay': 0.01,
        'max_grad_norm': 1.0,
        'warmup_steps': 500,
    }
    
    # M3 칩 최적화 설정
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        torch.backends.mps.enable_fallback_for_tf32 = True

    # 토크나이저 및 모델 초기화
    logger.info("토크나이저와 모델 초기화 중...")
    tokenizer = RecipeTokenizer()

    config = AutoConfig.from_pretrained(
        'klue/bert-base',
        num_labels=17,
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        vocab_size=len(tokenizer.tokenizer)  # 토크나이저의 vocab size 사용
    )
    
    model = RecipeBERTModel(config)
    # 토크나이저의 vocab size에 맞게 모델 임베딩 조정
    model.resize_token_embeddings(len(tokenizer.tokenizer))
    
    # 데이터셋 생성
    logger.info("데이터셋 생성 중...")
    train_dataset = RecipeDataset(train_recipes, tokenizer)
    val_dataset = RecipeDataset(val_recipes, tokenizer)
    
    # 학습 디렉토리 생성
    output_dir = Path(f'models/recipe_bert_{model_version}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 트레이너 초기화 및 학습
    logger.info("트레이너 초기화 중...")
    trainer = RecipeTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        training_params=training_params,
        output_dir=str(output_dir)
    )
    
    logger.info("학습 시작...")
    train_loss = trainer.train(num_epochs=training_params['num_epochs'])
    logger.info("학습 완료!")

    # 검증 데이터로 평가
    val_loss = trainer.evaluate()
    logger.info(f"검증 손실: {val_loss:.4f}")

    # 테스트 데이터로 최종 평가
    test_dataset = RecipeDataset(test_recipes, tokenizer)
    trainer.val_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=16,
        shuffle=False,
        num_workers=0,
        collate_fn=trainer.train_loader.collate_fn
    )
    
    test_loss = trainer.evaluate()
    logger.info(f"테스트 손실: {test_loss:.4f}")
    
    # MongoDB에 학습 결과 저장
    db_logger.log_training_results(
        model_version=model_version,
        train_loss=train_loss,
        val_loss=val_loss,
        test_loss=test_loss,
        training_params=training_params,
        model_path=str(output_dir)
    )
    logger.info("학습 결과가 MongoDB에 저장되었습니다.")

if __name__ == '__main__':
    main()