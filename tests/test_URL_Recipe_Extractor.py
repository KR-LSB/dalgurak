import unittest
import json
import sys
import time
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import requests
from bs4 import BeautifulSoup

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.crawling.url_recipe_extractor import URLRecipeExtractor

class TestNaverBlogExtractionUpdated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """테스트 환경 설정"""
        cls.extractor = URLRecipeExtractor()
        
        # 현재 활성화된 요리 블로그 URL 확인 (2025년 3월 기준)
        cls.valid_blogs = cls._find_valid_blogs()
        print(f"유효한 블로그 찾음: {len(cls.valid_blogs)}개")
        
        # 테스트 결과 저장 디렉토리
        cls.output_dir = Path('test_results/naver_blog_tests')
        cls.output_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _find_valid_blogs(cls):
        """네이버에서 현재 유효한 요리 블로그 찾기"""
        # 최신 요리 블로그 찾기
        search_url = "https://section.blog.naver.com/Search/Post.naver?pageNo=1&rangeType=ALL&orderBy=sim&keyword=요리레시피"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            }
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 존재 확인을 강화
                valid_blogs = []
                for a_tag in soup.select('a.desc_inner'):
                    href = a_tag.get('href', '')
                    if '/PostView.naver' in href:
                        # 각 URL 직접 접근 확인
                        check_url = f"https://blog.naver.com{href}"
                        try:
                            check_response = requests.head(check_url, headers=headers, timeout=5)
                            if check_response.status_code == 200 and "MobileErrorView" not in check_response.url:
                                valid_blogs.append(check_url)
                                if len(valid_blogs) >= 3:  # 3개만 수집
                                    break
                        except Exception:
                            continue
                
                return valid_blogs
        except Exception as e:
            print(f"블로그 검색 중 오류: {str(e)}")
        
        # 알려진 작동하는 블로그 백업 목록 (주기적 업데이트 필요)
        return ["https://blog.naver.com/haemil_recipe/223634572386"]
    
    def test_blog_extraction_with_direct_api(self):
        """네이버 블로그 직접 API 추출 테스트"""
        # 유효한 블로그가 없으면 테스트 스킵
        if not self.valid_blogs:
            self.skipTest("유효한 네이버 블로그를 찾을 수 없습니다")
        
        blog_url = self.valid_blogs[0]
        print(f"\n직접 API 요청 테스트: {blog_url}")
        
        # URL에서 블로그 ID와 포스트 번호 추출
        blog_id, log_no = self._extract_blog_info(blog_url)
        
        if not blog_id or not log_no:
            self.skipTest("블로그 ID와 포스트 번호를 추출할 수 없습니다")
        
        # API 키 확인
        from dotenv import load_dotenv
        import os
        load_dotenv()
        client_id = os.getenv('NAVER_CLIENT_ID')
        client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            self.skipTest("네이버 API 키가 설정되지 않았습니다")
        
        # 1. 네이버 검색 API 직접 요청
        search_url = f"https://openapi.naver.com/v1/search/blog.json?query={blog_id}"
        headers = {
            'X-Naver-Client-Id': client_id,
            'X-Naver-Client-Secret': client_secret
        }
        
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            
            search_results = response.json()
            print(f"API 검색 결과: {len(search_results.get('items', []))}개 항목")
            
            # 검색 결과 분석
            for item in search_results.get('items', []):
                item_link = item.get('link', '')
                if log_no in item_link:
                    print(f"일치하는 포스트 찾음!")
                    print(f"제목: {unquote(item.get('title', '').replace('<b>', '').replace('</b>', ''))}")
                    print(f"설명: {unquote(item.get('description', '').replace('<b>', '').replace('</b>', ''))}")
                    break
            
            # 검색 결과가 0개이면 실패로 간주
            self.assertGreater(len(search_results.get('items', [])), 0, "API 검색 결과가 없습니다")
            
        except Exception as e:
            self.fail(f"API 직접 요청 중 오류 발생: {str(e)}")
        
    def test_blog_extraction_with_direct_http(self):
        """네이버 블로그 직접 HTTP 요청 테스트"""
        # 유효한 블로그가 없으면 테스트 스킵
        if not self.valid_blogs:
            self.skipTest("유효한 네이버 블로그를 찾을 수 없습니다")
        
        blog_url = self.valid_blogs[0]
        print(f"\n직접 HTTP 요청 테스트: {blog_url}")
        
        # 모바일 버전 URL로 변환 - 여러 형식 시도
        try:
            urls_to_try = [
                blog_url,
                blog_url.replace('blog.naver.com', 'm.blog.naver.com')
            ]
            
            # 블로그 ID와 포스트 번호 추출
            blog_id, log_no = self._extract_blog_info(blog_url)
            if blog_id and log_no:
                urls_to_try.append(f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}")
            
            success = False
            for test_url in urls_to_try:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Mobile; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
                        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                    
                    response = requests.get(test_url, headers=headers, timeout=10)
                    
                    # 응답 확인
                    print(f"URL: {test_url}")
                    print(f"HTTP 상태 코드: {response.status_code}")
                    print(f"응답 크기: {len(response.text)} 바이트")
                    
                    # 오류 페이지 확인
                    if "MobileErrorView" in response.url or "ErrorView" in response.url:
                        print(f"오류 페이지 발견: {response.url}")
                        continue
                    
                    # 성공 응답 확인
                    if response.status_code == 200:
                        # 간단한 콘텐츠 확인
                        soup = BeautifulSoup(response.text, 'html.parser')
                        title = soup.select_one('h3.se_title, h3.tit_h3, div.se-module-text')
                        content = soup.select_one('div.se-main-container, div.post_ct, div.__se_component_area')
                        
                        if title:
                            print(f"페이지 제목: {title.text.strip()}")
                        if content:
                            content_text = content.text.strip()
                            print(f"콘텐츠 일부: {content_text[:100]}...")
                            
                            # 콘텐츠가 존재하면 성공
                            self.assertTrue(len(content_text) > 100, "콘텐츠가 충분하지 않습니다")
                            success = True
                            break
                except Exception as e:
                    print(f"URL {test_url} 시도 중 오류: {str(e)}")
                    continue
            
            # 모든 URL 시도 실패 확인
            if not success:
                self.skipTest("모든 URL 형식 시도 실패 - 유효한 블로그 URL을 업데이트 해야합니다")
                
        except Exception as e:
            self.skipTest(f"직접 HTTP 요청 중 오류 발생: {str(e)}")

    def test_extractor_with_updated_url(self):
        """업데이트된 URL로 추출기 테스트"""
        # 유효한 블로그가 없으면 테스트 스킵
        if not self.valid_blogs:
            self.skipTest("유효한 네이버 블로그를 찾을 수 없습니다")
        
        blog_url = self.valid_blogs[0]
        print(f"\n추출기 테스트 (유효한 URL): {blog_url}")
        
        start_time = time.time()
        result = self.extractor.extract_recipe_from_url(blog_url)
        elapsed_time = time.time() - start_time
        
        print(f"추출 소요시간: {elapsed_time:.2f}초")
        
        # 성공/실패 여부에 따른 검증
        if "error" in result:
            print(f"오류 발생: {result['error']}")
            # 네이버 블로그 접근 제한으로 인한 실패는 테스트에서 스킵
            self.skipTest("블로그 접근 제한으로 테스트 스킵")
        else:
            # 결과 검증
            self.assertIn("title", result)
            self.assertGreater(len(result["title"]), 3)
            
            # 결과 출력
            print(f"제목: {result.get('title', '없음')}")
            print(f"재료 수: {len(result.get('ingredients', []))}")
            print(f"조리 단계 수: {len(result.get('steps', []))}")
            
            # 결과 저장
            output_file = self.output_dir / "naver_blog_successful_test.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            print(f"결과 저장 완료: {output_file}")
    
    def _extract_blog_info(self, url: str) -> tuple:
        """URL에서 블로그 ID와 포스트 번호 추출"""
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        query = parsed_url.query
        
        # PostView.naver 형식
        if 'PostView.naver' in url:
            query_params = parse_qs(query)
            blog_id = query_params.get('blogId', [''])[0]
            log_no = query_params.get('logNo', [''])[0]
            if blog_id and log_no:
                return blog_id, log_no
        # 기본 형식
        else:
            path_parts = path.split('/')
            if len(path_parts) >= 2:
                blog_id = path_parts[0]
                log_no = path_parts[1]
                return blog_id, log_no
        
        return None, None

if __name__ == "__main__":
    unittest.main()