# src/embedding/generate_embeddings.py

from recipe_embedder import RecipeEmbedder
from pathlib import Path
import json
import logging

def main():
    # 1. 로깅 설정
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # 2. 전처리된 데이터 로드
        logger.info("전처리된 데이터 로드 중...")
        processed_files = list(Path('data/processed').glob('processed_recipes_*.json'))
        if not processed_files:
            raise FileNotFoundError("전처리된 레시피 파일을 찾을 수 없습니다.")
        
        latest_file = max(processed_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"최신 데이터 파일: {latest_file}")

        with open(latest_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        
        logger.info(f"총 {len(recipes)}개의 레시피 로드 완료")

        # 3. 임베딩 생성
        logger.info("임베딩 생성 시작...")
        embedder = RecipeEmbedder()
        
        # 4. 벡터 데이터베이스 생성
        persist_directory = "data/recipe_db"
        vectordb = embedder.create_vector_store(recipes, persist_directory)
        
        logger.info("임베딩 생성 완료")
        return vectordb

    except Exception as e:
        logger.error(f"임베딩 생성 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main()