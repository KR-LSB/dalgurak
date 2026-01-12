"""
레시피 임베딩 생성기

레시피 데이터를 벡터로 변환하여 Chroma DB에 저장합니다.

Features:
    - 레시피 데이터 텍스트 변환
    - OpenAI 임베딩 생성
    - Chroma 벡터 DB 저장
    - 배치 처리 지원
    - 유사 레시피 검색

Example:
    >>> embedder = RecipeEmbedder(persist_directory="recipe_db")
    >>> recipes = embedder.load_recipes("data/processed/recipes.json")
    >>> embedder.create_embeddings(recipes)
    >>> results = embedder.search("김치찌개 만드는 법")
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from tqdm import tqdm

logger = logging.getLogger(__name__)


class RecipeEmbedder:
    """
    레시피 임베딩 생성기
    
    처리된 레시피 데이터를 벡터로 변환하여 
    Chroma 벡터 DB에 저장합니다.
    
    Args:
        persist_directory: 벡터 DB 저장 경로 (기본값: "recipe_db")
        chunk_size: 텍스트 청크 크기 (기본값: 500)
        chunk_overlap: 청크 간 중첩 크기 (기본값: 50)
    
    Attributes:
        vectordb: Chroma 벡터 데이터베이스 인스턴스
    """
    
    def __init__(
        self,
        persist_directory: str = "recipe_db",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        load_dotenv()
        
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 임베딩 모델 초기화
        self.embeddings = OpenAIEmbeddings()
        
        # 텍스트 분할기
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],
            length_function=len
        )
        
        # 벡터 DB (지연 초기화)
        self.vectordb: Optional[Chroma] = None
        
        logger.info(
            f"RecipeEmbedder 초기화 완료 "
            f"(chunk_size={chunk_size}, overlap={chunk_overlap})"
        )

    def load_recipes(self, filepath: str) -> List[Dict]:
        """
        레시피 데이터 로드
        
        Args:
            filepath: JSON 파일 경로
            
        Returns:
            레시피 목록
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 형식에 따라 처리
        if isinstance(data, dict) and 'recipes' in data:
            recipes = data['recipes']
        elif isinstance(data, list):
            recipes = data
        else:
            raise ValueError("지원하지 않는 데이터 형식입니다.")

        logger.info(f"{len(recipes)}개 레시피 로드 완료: {filepath}")
        return recipes

    def recipe_to_text(self, recipe: Dict) -> str:
        """
        레시피를 검색 가능한 텍스트로 변환
        
        벡터 검색에 최적화된 형식으로 레시피 정보를 텍스트화합니다.
        
        Args:
            recipe: 레시피 딕셔너리
            
        Returns:
            변환된 텍스트
        """
        parts = []

        # 제목 (가중치 높음)
        if recipe.get('title'):
            parts.append(f"제목: {recipe['title']}")
            parts.append(f"요리명: {recipe['title']}")  # 검색 다양성

        # 카테고리
        if recipe.get('category'):
            parts.append(f"카테고리: {recipe['category']}")

        # 난이도
        if recipe.get('difficulty'):
            parts.append(f"난이도: {recipe['difficulty']}")

        # 조리 시간
        if recipe.get('cooking_time'):
            parts.append(f"조리시간: {recipe['cooking_time']}분")

        # 인분
        if recipe.get('servings'):
            parts.append(f"분량: {recipe['servings']}인분")

        # 재료
        if recipe.get('ingredients'):
            if isinstance(recipe['ingredients'][0], dict):
                ing_list = [
                    ing.get('original', ing.get('name', ''))
                    for ing in recipe['ingredients']
                ]
            else:
                ing_list = recipe['ingredients']
            
            if ing_list:
                parts.append(f"재료: {', '.join(ing_list)}")

        # 조리 단계
        if recipe.get('steps'):
            if isinstance(recipe['steps'][0], dict):
                steps_text = ' '.join([
                    f"{s['order']}. {s['description']}"
                    for s in recipe['steps']
                ])
            else:
                steps_text = ' '.join([
                    f"{i+1}. {s}"
                    for i, s in enumerate(recipe['steps'])
                ])
            parts.append(f"조리방법: {steps_text}")

        # 설명
        if recipe.get('description'):
            parts.append(f"설명: {recipe['description']}")

        return "\n".join(parts)

    def create_embeddings(
        self,
        recipes: List[Dict],
        batch_size: int = 100,
        show_progress: bool = True
    ) -> Chroma:
        """
        레시피 임베딩 생성 및 벡터 DB 저장
        
        Args:
            recipes: 레시피 목록
            batch_size: 배치 크기
            show_progress: 진행률 표시 여부
            
        Returns:
            Chroma 벡터 DB 인스턴스
        """
        texts = []
        metadatas = []

        logger.info("레시피 텍스트 변환 중...")

        iterator = tqdm(recipes, desc="텍스트 변환") if show_progress else recipes
        
        for recipe in iterator:
            text = self.recipe_to_text(recipe)
            
            # 텍스트 청크 분할
            chunks = self.text_splitter.split_text(text)

            for chunk in chunks:
                texts.append(chunk)
                metadatas.append({
                    'title': recipe.get('title', ''),
                    'category': recipe.get('category', ''),
                    'difficulty': recipe.get('difficulty', ''),
                    'source': recipe.get('source', ''),
                    'recipe_id': recipe.get('id', ''),
                    'url': recipe.get('url', '')
                })

        logger.info(f"총 {len(texts)}개 텍스트 청크 생성")

        # 벡터 DB 생성
        logger.info("임베딩 생성 및 벡터 DB 저장 중...")
        
        self.vectordb = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"벡터 DB 저장 완료: {self.persist_directory}")

        return self.vectordb

    def add_recipes(
        self,
        recipes: List[Dict],
        show_progress: bool = True
    ) -> None:
        """
        기존 DB에 레시피 추가
        
        Args:
            recipes: 추가할 레시피 목록
            show_progress: 진행률 표시 여부
        """
        if self.vectordb is None:
            self.vectordb = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )

        texts = []
        metadatas = []

        iterator = tqdm(recipes, desc="레시피 추가") if show_progress else recipes
        
        for recipe in iterator:
            text = self.recipe_to_text(recipe)
            chunks = self.text_splitter.split_text(text)

            for chunk in chunks:
                texts.append(chunk)
                metadatas.append({
                    'title': recipe.get('title', ''),
                    'category': recipe.get('category', ''),
                    'difficulty': recipe.get('difficulty', ''),
                    'source': recipe.get('source', ''),
                    'recipe_id': recipe.get('id', ''),
                    'url': recipe.get('url', '')
                })

        self.vectordb.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"{len(recipes)}개 레시피 ({len(texts)}개 청크) 추가 완료")

    def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """
        유사 레시피 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 결과 수
            filter_dict: 메타데이터 필터 (예: {'category': '국/탕/찌개'})
            
        Returns:
            검색 결과 목록
        """
        if self.vectordb is None:
            self.vectordb = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )

        search_kwargs = {"k": k}
        if filter_dict:
            search_kwargs["filter"] = filter_dict

        results = self.vectordb.similarity_search_with_score(
            query, 
            **search_kwargs
        )

        return [
            {
                'content': doc.page_content,
                'metadata': doc.metadata,
                'score': float(score)
            }
            for doc, score in results
        ]

    def search_by_category(
        self,
        query: str,
        category: str,
        k: int = 5
    ) -> List[Dict]:
        """
        카테고리 필터링 검색
        
        Args:
            query: 검색 쿼리
            category: 카테고리명
            k: 반환할 결과 수
            
        Returns:
            검색 결과 목록
        """
        return self.search(query, k, filter_dict={'category': category})

    def get_stats(self) -> Dict[str, Any]:
        """
        벡터 DB 통계 반환
        
        Returns:
            total_documents: 총 문서 수
            persist_directory: 저장 경로
            chunk_size: 청크 크기
            chunk_overlap: 청크 중첩
        """
        if self.vectordb is None:
            self.vectordb = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )

        collection = self.vectordb._collection

        return {
            'total_documents': collection.count(),
            'persist_directory': self.persist_directory,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }

    def delete_by_ids(self, ids: List[str]) -> None:
        """
        ID로 문서 삭제
        
        Args:
            ids: 삭제할 문서 ID 목록
        """
        if self.vectordb is None:
            self.vectordb = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )

        self.vectordb._collection.delete(ids=ids)
        logger.info(f"{len(ids)}개 문서 삭제 완료")

    def clear(self) -> None:
        """벡터 DB 전체 초기화"""
        import shutil
        
        if Path(self.persist_directory).exists():
            shutil.rmtree(self.persist_directory)
            logger.info(f"벡터 DB 삭제 완료: {self.persist_directory}")
        
        self.vectordb = None


def main():
    """임베딩 생성 CLI"""
    import argparse

    parser = argparse.ArgumentParser(description='레시피 임베딩 생성')
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='입력 JSON 파일'
    )
    parser.add_argument(
        '--output', '-o',
        default='recipe_db',
        help='출력 디렉토리 (기본값: recipe_db)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='청크 크기 (기본값: 500)'
    )
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=50,
        help='청크 중첩 (기본값: 50)'
    )

    args = parser.parse_args()

    embedder = RecipeEmbedder(
        persist_directory=args.output,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )

    recipes = embedder.load_recipes(args.input)
    embedder.create_embeddings(recipes)

    stats = embedder.get_stats()
    print(f"\n임베딩 생성 완료!")
    print(f"  - 총 문서 수: {stats['total_documents']}")
    print(f"  - 저장 경로: {stats['persist_directory']}")


if __name__ == '__main__':
    main()