from pymongo import MongoClient
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

class ModelLogger:
    def __init__(self):
        try:
            load_dotenv()
            username = os.getenv('MONGODB_USERNAME')
            password = os.getenv('MONGODB_PASSWORD')
            cluster = os.getenv('MONGODB_CLUSTER')
            
            self.uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=lsb"
            
            self.client = MongoClient(self.uri)
            self.db = self.client['recipe_db']
            self.model_results = self.db['model_results']
            
        except Exception as e:
            print(f"MongoDB 연결 초기화 중 오류 발생: {e}")
            raise

    def log_training_results(self, 
                           model_version: str,
                           train_loss: float,
                           val_loss: float,
                           test_loss: float,
                           training_params: dict,
                           model_path: str):
        """학습 결과를 MongoDB에 저장"""
        try:
            result = {
                'model_version': model_version,
                'timestamp': datetime.now(),
                'metrics': {
                    'train_loss': train_loss,
                    'val_loss': val_loss,
                    'test_loss': test_loss
                },
                'training_params': training_params,
                'model_path': model_path,
                'data_version': '20250108_140835'  # 현재 사용 중인 데이터 버전
            }
            
            self.model_results.insert_one(result)
            print(f"학습 결과가 MongoDB에 저장되었습니다.")
            
        except Exception as e:
            print(f"학습 결과 저장 중 오류 발생: {e}")
            
    def get_latest_results(self):
        """가장 최근의 학습 결과 조회"""
        return self.model_results.find_one(
            sort=[('timestamp', -1)]
        )