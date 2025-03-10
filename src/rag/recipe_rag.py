from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory.buffer import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import os


class RecipeRAG:
    def __init__(self, persist_directory: str = "recipe_db"):

        load_dotenv()

        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

        self.logger = self._setup_logger()
        self.embeddings = OpenAIEmbeddings()
        self.vectordb = Chroma(persist_directory=persist_directory, 
                             embedding_function=self.embeddings)
        
        # LLM 설정
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo-16k",
            temperature=0.7
        )
        
        # 대화 기억 설정
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # RAG Chain 설정
        self.qa_chain = self._setup_qa_chain()

    def _setup_logger(self):
        logger = logging.getLogger('RecipeRAG')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            fh = logging.FileHandler('recipe_rag.log')
            ch = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            logger.addHandler(fh)
            logger.addHandler(ch)
        
        return logger

    def _setup_qa_chain(self):
        # 프롬프트 템플릿 설정
        template = """당신은 요리 전문가입니다. 제공된 레시피 정보를 바탕으로 사용자의 질문에 친절하게 답변해주세요.

컨텍스트: {context}

질문: {question}

답변을 할 때 다음 사항을 지켜주세요:
- 레시피와 관련된 구체적인 정보 제공
- 필요한 경우 조리 팁이나 대체 재료 제안
- 명확하고 이해하기 쉬운 설명
- 질문과 관련 없는 정보는 제외

답변:"""

        QA_PROMPT = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectordb.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            ),
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT}
        )

    def ask(self, question: str) -> str:
        """질문에 대한 답변 생성"""
        try:
            response = self.qa_chain.invoke({"question": question})
            return response['answer']
        except Exception as e:
            self.logger.error(f"답변 생성 중 오류 발생: {str(e)}")
            return f"죄송합니다. 답변을 생성하는 중에 오류가 발생했습니다: {str(e)}"