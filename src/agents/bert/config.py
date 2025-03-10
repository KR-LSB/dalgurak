from transformers import BertConfig

def get_recipe_bert_config():
    config = BertConfig.from_pretrained(
        'skt/kobert-base-v1',
        num_labels=17,  # 카테고리 수
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1
    )
    
    # 레시피 특화 설정 추가
    config.max_position_embeddings = 512
    config.max_steps = 30  # 최대 레시피 단계 수
    config.learning_rate = 2e-5
    config.num_train_epochs = 3
    config.per_device_train_batch_size = 16
    config.gradient_accumulation_steps = 2
    config.warmup_steps = 500
    config.weight_decay = 0.01
    
    return config

# 학습 관련 설정
TRAINING_CONFIG = {
    'output_dir': './models/recipe_bert',
    'logging_dir': './logs/recipe_bert',
    'logging_steps': 100,
    'save_steps': 1000,
    'eval_steps': 500,
    'seed': 42
}

# 데이터 관련 설정
DATA_CONFIG = {
    'train_ratio': 0.8,
    'val_ratio': 0.1,
    'test_ratio': 0.1,
    'max_length': 512
}

# 모델 하이퍼파라미터
MODEL_CONFIG = {
    'hidden_size': 768,
    'num_attention_heads': 12,
    'num_hidden_layers': 12,
    'intermediate_size': 3072
}