from pymongo import MongoClient
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchTitleUpdater:
    def __init__(self):
        try:
            load_dotenv()
            username = os.getenv('MONGODB_USERNAME')
            password = os.getenv('MONGODB_PASSWORD')
            cluster = os.getenv('MONGODB_CLUSTER')
            
            self.uri = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority&appName=lsb"
            
            print("Connecting with URI:", self.uri.replace(self.uri.split(':')[2].split('@')[0], '****'))
            
            self.client = MongoClient(self.uri)
            self.db = self.client['recipe_db']
            self.recipes = self.db['recipes']
            
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        except Exception as e:
            print(f"초기화 중 오류 발생: {e}")
            raise

    def fetch_title(self, url: str) -> Optional[str]:
        """URL에서 레시피 제목 가져오기"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_selectors = [
                "h3.view2_summary > strong",
                "div.view2_summary h3",
                "div.view2_top > h3",
                "h3[itemprop='name']",
                "meta[property='og:title']"
            ]
            
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get('content') if selector.startswith('meta') else element.text
                    title = title.strip()
                    if title:
                        return title
            
            return None
            
        except Exception as e:
            logger.error(f"제목 가져오기 실패 ({url}): {str(e)}")
            return None

    def update_recipe_titles(self, max_workers: int = 5):
        """모든 레시피의 제목 업데이트"""
        try:
            # 제목이 없거나 비어있는 레시피 찾기
            recipes_to_update = list(self.recipes.find(
                {"$or": [
                    {"title": {"$exists": False}},
                    {"title": None},
                    {"title": ""},
                    {"title": {"$regex": "^\\s*$"}}  # 공백만 있는 경우
                ]},
                {"_id": 1, "url": 1}
            ))

            total_recipes = len(recipes_to_update)
            logger.info(f"업데이트가 필요한 레시피 수: {total_recipes}")

            if total_recipes == 0:
                logger.info("업데이트가 필요한 레시피가 없습니다.")
                return

            successful_updates = 0
            failed_updates = 0

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for i, recipe in enumerate(recipes_to_update, 1):
                    try:
                        url = recipe['url']
                        title = self.fetch_title(url)
                        
                        if title:
                            self.recipes.update_one(
                                {"_id": recipe["_id"]},
                                {"$set": {"title": title}}
                            )
                            successful_updates += 1
                            logger.info(f"[{i}/{total_recipes}] 성공: {url} -> {title}")
                        else:
                            failed_updates += 1
                            logger.warning(f"[{i}/{total_recipes}] 실패: {url}")
                        
                        # 요청 간격 조절
                        time.sleep(0.5)
                        
                        # 진행상황 로깅 (10개마다)
                        if i % 10 == 0:
                            logger.info(f"진행 상황: {i}/{total_recipes} "
                                      f"(성공: {successful_updates}, 실패: {failed_updates})")
                            
                    except Exception as e:
                        failed_updates += 1
                        logger.error(f"레시피 업데이트 실패 ({recipe.get('url', 'Unknown URL')}): {str(e)}")

            logger.info("\n=== 최종 결과 ===")
            logger.info(f"전체 레시피: {total_recipes}")
            logger.info(f"성공: {successful_updates}")
            logger.info(f"실패: {failed_updates}")
            
        except Exception as e:
            logger.error(f"전체 업데이트 프로세스 실패: {str(e)}")
        finally:
            self.client.close()

def main():
    updater = BatchTitleUpdater()
    updater.update_recipe_titles()

if __name__ == "__main__":
    main()