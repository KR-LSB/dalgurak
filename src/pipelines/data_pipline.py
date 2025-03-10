from src.preprocessing import recipe_processor
from src.agents.rag import embeddings
from src.tools.utils import data_validator

class RecipeDataPipeline:
    def __init__(self):
        self.processor = recipe_processor.RecipeProcessor()
        self.embedder = embeddings.RecipeEmbedder()
        
    def run(self, raw_data):
        # 1. 데이터 전처리
        processed_data = self.processor.process(raw_data)
        
        # 2. 데이터 검증
        validated_data = data_validator.validate(processed_data)
        
        # 3. 임베딩 생성
        embeddings = self.embedder.create_embeddings(validated_data)
        
        return embeddings