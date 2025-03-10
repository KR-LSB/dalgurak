import torch
import torch.nn as nn
from transformers import BertModel, PreTrainedModel
from typing import Optional, Dict, Union
import torch.nn.functional as F

class RecipeBERTModel(PreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        
        # vocab_size 업데이트 (special tokens 고려)
        config.vocab_size = 32006  # tokenizer의 vocabulary size와 맞춤
        
        # BERT 기본 모델
        self.bert = BertModel(config)
        
        # Dropout
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        
        # 각 태스크를 위한 분류기 헤드
        self.category_classifier = nn.Linear(config.hidden_size, 17)  # 17개 카테고리
        self.difficulty_classifier = nn.Linear(config.hidden_size, 3)  # 3개 난이도
        self.time_classifier = nn.Linear(config.hidden_size, 3)  # 3개 시간대
        
        # 초기화
        self.post_init()
        
    def resize_token_embeddings(self, new_num_tokens: int):
        """토큰 임베딩 크기 조정"""
        self.bert.resize_token_embeddings(new_num_tokens)
        
    def forward(
        self,
        input_ids: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        token_type_ids: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
        labels: Optional[Dict[str, torch.Tensor]] = None
    ) -> Dict[str, torch.Tensor]:
        # 입력 유효성 검사
        if input_ids is not None:
            batch_size, seq_len = input_ids.size()
            if seq_len > 512:
                raise ValueError(f"Input sequence length ({seq_len}) exceeds model's maximum length (512)")
        
        # BERT 모델 출력
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids
        )
        
        pooled_output = outputs[1]
        pooled_output = self.dropout(pooled_output)
        
        # 각 태스크에 대한 예측
        category_logits = self.category_classifier(pooled_output)
        difficulty_logits = self.difficulty_classifier(pooled_output)
        time_logits = self.time_classifier(pooled_output)
        
        output_dict = {
            'category_logits': category_logits,
            'difficulty_logits': difficulty_logits,
            'time_logits': time_logits
        }
        
        # 학습 시 손실 계산
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            
            category_loss = loss_fct(
                category_logits, 
                labels['category'].view(-1)
            )
            difficulty_loss = loss_fct(
                difficulty_logits, 
                labels['difficulty'].view(-1)
            )
            time_loss = loss_fct(
                time_logits, 
                labels['time'].view(-1)
            )
            
            # 전체 손실은 각 태스크 손실의 가중 합
            total_loss = (
                category_loss * 0.4 +  # 카테고리 분류가 가장 중요
                difficulty_loss * 0.3 +
                time_loss * 0.3
            )
            
            output_dict['loss'] = total_loss
        
        return output_dict