# test_env.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def test_langchain():
    # 환경변수 로드
    load_dotenv()
    
    # API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"API Key loaded: {api_key[:10]}...")  # API 키의 처음 10자리만 출력
    
    chat = ChatOpenAI(model="gpt-3.5-turbo")  # 모델 명시적 지정
    message = HumanMessage(content="Hello!")
    response = chat.invoke([message])
    print("Response:", response)

if __name__ == "__main__":
    test_langchain()