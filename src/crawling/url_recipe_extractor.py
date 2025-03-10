from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, Any, Optional
import traceback
import time
from src.crawling.parsers.recipe_parsers import TenThousandRecipeParser, NaverRecipeParser
from src.crawling.parsers.generic_recipe_parser import GenericRecipeParser
from src.crawling.parsers.naver_blog_api_parser import NaverBlogAPIParser

class URLRecipeExtractor:
    """URL에서 레시피 정보를 추출하는 클래스"""
    
    def __init__(self):
        # 로깅 설정
        self.logger = logging.getLogger('URLRecipeExtractor')
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # 지원 도메인 및 파서 설정
        self.parsers = {
            "10000recipe.com": TenThousandRecipeParser(),
            "terms.naver.com": NaverRecipeParser()
        }
        
        # 범용 파서 설정
        self.generic_parser = GenericRecipeParser()
        
        # 요청 제한
        self.request_delay = 3  # 초 단위 대기시간
        self._last_request_time = 0
        # 네이버 블로그 API 파서 추가
        try:
            self.naver_blog_parser = NaverBlogAPIParser()
        except ValueError as e:
            self.logger.warning(f"네이버 블로그 API 파서 초기화 실패: {str(e)}")
            self.naver_blog_parser = None

    def _get_valid_url(self, url: str) -> str:
        """원본 및 모바일 URL 모두 시도하여 유효한 URL 반환"""
        # 원본 URL 확인
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        
        try:
            response = requests.head(url, headers=headers, timeout=5)
            if response.status_code == 200 and "ErrorView" not in response.url:
                return url
        except Exception:
            pass
            
        # 모바일 URL 시도
        try:
            mobile_url = url.replace('blog.naver.com', 'm.blog.naver.com')
            response = requests.head(mobile_url, headers=headers, timeout=5)
            if response.status_code == 200 and "ErrorView" not in response.url:
                return mobile_url
        except Exception:
            pass
            
        # PostView 형식 URL 시도 (다른 형식 시도)
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2:
                blog_id = path_parts[0]
                log_no = path_parts[1]
                alternate_url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
                response = requests.head(alternate_url, headers=headers, timeout=5)
                if response.status_code == 200 and "ErrorView" not in response.url:
                    return alternate_url
        except Exception:
            pass
            
        # 모든 시도 실패 시 원본 URL 반환
        return url
    
    def _check_url_exists(self, url: str) -> tuple:
        """URL이 존재하는지 확인하고 결과와 오류 메시지 반환"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            }
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
            
            # 오류 페이지로 리다이렉트 확인
            if "ErrorView" in response.url:
                error_msg = "존재하지 않는 블로그입니다"
                if "해당+블로그가+없습니다" in response.url:
                    error_msg = "해당 블로그가 존재하지 않습니다"
                elif "접근이+제한되었습니다" in response.url:
                    error_msg = "해당 블로그는 접근이 제한되어 있습니다"
                
                return False, error_msg
                
            # 상태 코드 확인
            if response.status_code != 200:
                return False, f"서버 응답 오류: {response.status_code}"
                
            return True, ""
            
        except requests.RequestException as e:
            return False, f"요청 오류: {str(e)}"
        except Exception as e:
            return False, f"처리 중 오류 발생: {str(e)}"

    def extract_recipe_from_url(self, url: str) -> Dict[str, Any]:
        """URL에서 레시피 정보 추출 (개선된 오류 처리)"""
        try:
            # URL 형식 검증
            if not url.startswith(('http://', 'https://')):
                return {"error": "유효한 URL이 아닙니다. http:// 또는 https://로 시작해야 합니다."}
            
            # URL 검증 및 수정
            valid_url = self._get_valid_url(url)
            if valid_url != url:
                self.logger.info(f"URL 변환됨: {url} -> {valid_url}")
                url = valid_url
                
            # URL 존재 확인
            exists, error_msg = self._check_url_exists(url)
            if not exists:
                return {
                    "error": error_msg,
                    "error_type": "not_found",
                    "url": url,
                    "status": "failed"
                }
            
            # 도메인 추출 및 지원 여부 확인
            domain = urlparse(url).netloc
            self.logger.info(f"URL 처리 시작: {url} (도메인: {domain})")
            
            # 요청 간격 유지 (크롤링 정책 준수)
            self._respect_rate_limit()
            
            # 네이버 블로그 URL 확인
            if 'blog.naver.com' in domain and hasattr(self, 'naver_blog_parser') and self.naver_blog_parser:
                self.logger.info(f"네이버 블로그 API 파서 사용: {url}")
                try:
                    # API로 블로그 정보 가져오기
                    blog_content = self.naver_blog_parser.extract_blog_info(url)
                    if blog_content:
                        # 레시피 정보 추출
                        recipe = self.naver_blog_parser.parse_recipe_from_content(blog_content)
                        recipe['url'] = url
                        recipe['domain'] = domain
                        recipe['extracted_at'] = datetime.now().isoformat()
                        recipe['parser_type'] = "네이버 블로그 API 파서"
                        return recipe
                    else:
                        self.logger.warning(f"네이버 블로그 API로 내용을 가져오지 못했습니다: {url}")
                except Exception as e:
                    self.logger.error(f"네이버 블로그 API 처리 중 오류: {str(e)}")
            
            # 페이지 내용 가져오기
            response = self._fetch_page(url)
            if isinstance(response, dict) and "error" in response:
                return response
                
            # HTML 파싱
            soup = BeautifulSoup(response, 'html.parser')
            
            # 적절한 파서 선택
            parser = self._select_parser(domain)
            parser_type = "전용 파서" if domain in self.parsers else "범용 파서"
            
            # 레시피 정보 추출
            start_time = time.time()
            
            title = parser.parse_title(soup)
            self.logger.info(f"제목 추출: {title}")
            
            # 추출 내용 검증 - 제목이 너무 짧거나 일반적인 오류 페이지 제목인지
            if not title or len(title) < 3 or title in ["네이버 블로그", "Error", "오류 안내"]:
                return {
                    "error": "레시피 콘텐츠를 찾을 수 없습니다",
                    "error_type": "no_content",
                    "url": url,
                    "status": "failed"
                }
            
            ingredients = parser.parse_ingredients(soup)
            self.logger.info(f"재료 {len(ingredients)}개 추출")
            
            steps = parser.parse_steps(soup)
            self.logger.info(f"조리 단계 {len(steps)}개 추출")
            
            metadata = parser.parse_metadata(soup)
            self.logger.info(f"메타데이터 추출: {metadata}")
            
            # 결과 구성
            extraction_time = time.time() - start_time
            self.logger.info(f"추출 완료 (소요시간: {extraction_time:.2f}초)")
            
            result = {
                'url': url,
                'domain': domain,
                'title': title,
                'ingredients': ingredients,
                'steps': steps,
                'metadata': metadata,
                'extracted_at': datetime.now().isoformat(),
                'extraction_time': extraction_time,
                'parser_type': parser_type,
                'status': 'success'
            }
            
            return result
            
        except Exception as e:
            error_msg = f"레시피 추출 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            return {
                "error": error_msg,
                "error_type": "exception",
                "url": url,
                "status": "failed"
            }

    def _respect_rate_limit(self):
        """요청 간격 준수"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self.request_delay:
            wait_time = self.request_delay - time_since_last_request
            self.logger.info(f"요청 간격 유지를 위해 {wait_time:.2f}초 대기")
            time.sleep(wait_time)
            
        self._last_request_time = time.time()
            
    def _fetch_page(self, url: str) -> str:
        """웹페이지 내용 가져오기 - 강화된 버전"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Referer': 'https://www.google.com/'
            }
            
            # 모바일 브라우저로도 시도하기 위한 헤더
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            
            self.logger.info(f"페이지 요청 중: {url}")
            
            # 최대 3번까지 재시도
            for attempt in range(3):
                try:
                    # 일반 PC 버전으로 시도
                    if attempt == 0:
                        response = requests.get(url, headers=headers, timeout=10)
                    # 모바일 버전으로 시도 
                    elif attempt == 1:
                        # 네이버 블로그면 모바일 URL로 변경
                        if 'blog.naver.com' in url and 'm.blog.naver.com' not in url:
                            mobile_url = url.replace('blog.naver.com', 'm.blog.naver.com')
                        else:
                            mobile_url = url
                        response = requests.get(mobile_url, headers=mobile_headers, timeout=10)
                    # 최후의 시도: 다른 쿠키/세션 사용
                    else:
                        session = requests.Session()
                        session.headers.update(headers)
                        # 더 기다리기
                        response = session.get(url, timeout=15)
                    
                    # 상태코드 확인
                    if response.status_code == 200:
                        # 인코딩 처리
                        response.encoding = response.apparent_encoding
                        self.logger.info(f"페이지 로드 성공 (크기: {len(response.text)} bytes, 시도: {attempt+1})")
                        return response.text
                    else:
                        self.logger.warning(f"페이지 요청 실패 (상태코드: {response.status_code}, 시도: {attempt+1})")
                        
                except requests.RequestException as req_error:
                    self.logger.warning(f"요청 실패 (시도 {attempt+1}): {str(req_error)}")
                    
                # 다음 시도 전 대기
                time.sleep(2)
                    
            # 모든 시도 실패
            error_msg = f"모든 시도 후 페이지 요청 실패: {url}"
            self.logger.error(error_msg)
            return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"페이지 요청 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
            
    def _select_parser(self, domain: str):
        """도메인에 적합한 파서 선택"""
        # 도메인 명칭 정리 (www. 제거)
        clean_domain = domain.replace('www.', '')
        
        # 지원 도메인 검사
        for supported_domain, parser in self.parsers.items():
            if supported_domain in clean_domain:
                self.logger.info(f"전용 파서 사용: {domain} (매칭: {supported_domain})")
                return parser
                
        # 지원하지 않는 도메인은 범용 파서 사용
        self.logger.info(f"지원하지 않는 도메인입니다. 범용 파서를 사용합니다: {domain}")
        return self.generic_parser
    
    def _analyze_blog_structure(self, url: str) -> Optional[Dict[str, str]]:
        """블로그 구조 분석을 통한 접근 방법 결정"""
        try:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            })
            
            response = session.head(url, allow_redirects=True, timeout=5)
            final_url = response.url
            
            # 리다이렉트 여부 확인
            if final_url != url:
                self.logger.info(f"URL 리다이렉트 감지: {url} -> {final_url}")
                
                # 네이버 블로그 ID/logNo 추출
                if 'blog.naver.com' in final_url:
                    from urllib.parse import urlparse, parse_qs
                    parsed_url = urlparse(final_url)
                    
                    # PostView.naver 형식
                    if 'PostView.naver' in final_url:
                        query_params = parse_qs(parsed_url.query)
                        blog_id = query_params.get('blogId', [''])[0]
                        log_no = query_params.get('logNo', [''])[0]
                        if blog_id and log_no:
                            return {'blog_id': blog_id, 'log_no': log_no, 'final_url': final_url}
                    
                    # /blogId/logNo 형식
                    else:
                        path = parsed_url.path.strip('/')
                        parts = path.split('/')
                        if len(parts) >= 2 and parts[1].isdigit():
                            return {'blog_id': parts[0], 'log_no': parts[1], 'final_url': final_url}
            
            # 모바일 버전으로 시도
            if 'blog.naver.com' in url and 'm.blog.naver.com' not in url:
                mobile_url = url.replace('blog.naver.com', 'm.blog.naver.com')
                mobile_response = session.head(mobile_url, allow_redirects=True, timeout=5)
                if mobile_response.status_code == 200:
                    return {'mobile_url': mobile_response.url}
                    
            return None
            
        except Exception as e:
            self.logger.error(f"블로그 구조 분석 중 오류: {str(e)}")
            return None