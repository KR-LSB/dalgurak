from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
import json
import os
from typing import List, Dict
import logging
from dotenv import load_dotenv



class RecipeEmbedder:
    def __init__(self):

        load_dotenv()
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

        self.logger = self._setup_logger()
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
    def _setup_logger(self):
        logger = logging.getLogger('RecipeEmbedder')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            fh = logging.FileHandler('recipe_embedding.log')
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            logger.addHandler(fh)
            logger.addHandler(ch)
        
        return logger

    def prepare_recipe_texts(self, recipes: List[Dict]) -> List[str]:
        """레시피를 텍스트로 변환"""
        texts = []
        for recipe in recipes:
            # 기본 정보
            text = f"제목: {recipe['title']}\n"
            text += f"카테고리: {recipe['category']}\n\n"
            
            # 재료 정보
            text += "재료:\n"
            for ingredient in recipe.get('ingredients', []):
                amount = ingredient.get('amount', {})
                text += f"- {ingredient['name']}: {amount.get('original', '')}\n"
            text += "\n"
            
            # 조리 단계
            text += "조리 방법:\n"
            for step in recipe.get('steps', []):
                text += f"{step['step_num']}. {step['description']}\n"
                
            texts.append(text)
            
        return texts

    def create_vector_store(self, recipes: List[Dict], persist_directory: str = "recipe_db"):
        """벡터 데이터베이스 생성"""
        try:
            self.logger.info("레시피 텍스트 준비 중...")
            texts = self.prepare_recipe_texts(recipes)
            
            self.logger.info("텍스트 분할 중...")
            chunks = self.text_splitter.split_text("\n\n".join(texts))
            
            self.logger.info(f"총 {len(chunks)}개의 청크 생성됨")
            
            self.logger.info("벡터 데이터베이스 생성 중...")
            vectordb = Chroma.from_texts(
                texts=chunks,
                embedding=self.embeddings,
                persist_directory=persist_directory
            )
            
            self.logger.info(f"벡터 데이터베이스가 {persist_directory}에 저장됨")
            return vectordb
            
        except Exception as e:
            self.logger.error(f"벡터 데이터베이스 생성 중 오류 발생: {str(e)}")
            raise