import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
import logging
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import json

class NaverBlogAPIParser:
    """네이버 블로그 API를 사용한 레시피 파서"""
    
    def __init__(self):
        # 로깅 설정
        self.logger = logging.getLogger('NaverBlogAPIParser')
        
        # API 키 로드
        load_dotenv()
        self.client_id = os.getenv('NAVER_CLIENT_ID')
        self.client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 설정되지 않았습니다.")
        
        # API 헤더 설정
        self.headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret
        }
    
    def extract_blog_info(self, url: str) -> Optional[Dict[str, Any]]:
        """URL에서 블로그 정보 추출 개선"""
        try:
            # URL에서 블로그 ID와 포스트 번호 추출
            blog_id, log_no = self._extract_blog_info_from_url(url)
            if not blog_id or not log_no:
                self.logger.error(f"유효한 네이버 블로그 URL이 아닙니다: {url}")
                return None
            
            # 향상된 API 파라미터
            # 1. 더 정확한 검색을 위해 blogId와 logNo 두 값 모두 포함
            search_query = f"{blog_id} {log_no}"
            # 2. 검색 결과 수 증가
            api_url = f"https://openapi.naver.com/v1/search/blog.json?query={search_query}&display=100&sort=sim"
            
            response = requests.get(api_url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # 더 정확한 포스트 찾기 로직
            for item in data.get('items', []):
                post_url = item.get('link', '')
                # blog.naver.com/{blogId}/{logNo} 또는 주소에 logNo가 포함된 여러 패턴 검사
                if (f"/{blog_id}/" in post_url and log_no in post_url) or \
                (f"blogId={blog_id}" in post_url and f"logNo={log_no}" in post_url):
                    # 포스트 내용 가져오기
                    post_content = self._get_post_content(post_url)
                    
                    result = {
                        'title': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                        'description': item.get('description', '').replace('<b>', '').replace('</b>', ''),
                        'link': post_url,
                        'bloggerName': item.get('bloggername', ''),
                        'content': post_content
                    }
                    return result
            
            # 추가: 더 넓은 검색으로 다시 시도
            if not data.get('items'):
                return self._fallback_search(blog_id, log_no)
                
            self.logger.warning(f"블로그 포스트를 찾을 수 없습니다: {url}")
            return None
            
        except Exception as e:
            self.logger.error(f"블로그 정보 추출 중 오류 발생: {str(e)}")
            return None

    def _extract_blog_info_from_url(self, url: str) -> tuple:
        """URL에서 블로그 ID와 포스트 번호 추출 - 강화 버전"""
        # URL 파싱
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        query = parsed_url.query
        
        # 패턴 1: blog.naver.com/PostView.naver?blogId=xxx&logNo=xxx
        if 'PostView.naver' in url:
            query_params = parse_qs(query)
            blog_id = query_params.get('blogId', [''])[0]
            log_no = query_params.get('logNo', [''])[0]
            if blog_id and log_no:
                return blog_id, log_no
        
        # 패턴 2: blog.naver.com/{blogId}/{logNo}
        path_parts = path.split('/')
        if len(path_parts) >= 2:
            blog_id = path_parts[0]
            # logNo가 숫자인지 확인 (일부 블로그는 카테고리 이름 사용)
            potential_log_no = path_parts[1]
            if potential_log_no.isdigit():
                return blog_id, potential_log_no
        
        # 패턴 3: 마스킹된 URL (gk******/222995558994)
        if '*' in path:
            path_parts = path.split('/')
            if len(path_parts) >= 2 and path_parts[1].isdigit():
                # 마스킹된 ID 처리
                blog_id = path_parts[0].replace('*', '')
                # 정규식으로 실제 ID 추론 시도
                if len(blog_id) >= 2:  # 최소 2자 이상의 ID 부분이 있는 경우
                    return blog_id, path_parts[1]
        
        # 패턴 4: 숨겨진 매개변수 처리 (일부 리다이렉트 URL)
        for param_name in ['blogId', 'blogid', 'id']:
            if param_name in query:
                query_params = parse_qs(query)
                blog_id = query_params.get(param_name, [''])[0]
                if blog_id:
                    # logNo 매개변수 찾기
                    for log_param in ['logNo', 'logno', 'postno', 'postId']:
                        log_no = query_params.get(log_param, [''])[0]
                        if log_no:
                            return blog_id, log_no
        
        # URL에서 숫자 패턴 찾기 (가장 마지막 수단)
        if path:
            numbers = re.findall(r'(\d{9,})', path)  # 네이버 logNo는 보통 9자리 이상
            if numbers:
                # logNo로 추정되는 숫자
                log_no = numbers[-1]  # 가장 마지막 숫자 사용
                
                # blogId 추출 시도
                parts = re.split(r'\d{9,}', path)
                if parts and parts[0]:
                    blog_id = parts[0].strip('/')
                    return blog_id, log_no
        
        return None, None
    
    def _get_post_content(self, url: str) -> str:
        """포스트 내용 가져오기 (API로는 전체 콘텐츠를 가져올 수 없어 추가 요청 필요)"""
        try:
            # 일반 브라우저처럼 보이는 헤더 설정
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://search.naver.com/'
            }
            
            # 모바일 버전으로 요청 (보통 더 접근하기 쉬움)
            mobile_url = url.replace('blog.naver.com', 'm.blog.naver.com')
            response = requests.get(mobile_url, headers=headers)
            
            if response.status_code != 200:
                return ""
                
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 모바일 블로그 본문 영역 (여러 선택자 시도)
            content_selectors = [
                'div.se-main-container',  # 스마트에디터 2
                'div.__se_component_area',  # 구 스마트에디터
                'div.post_ct',            # 모바일 블로그
                'div.se_component_wrap'   # 다른 버전
            ]
            
            for selector in content_selectors:
                content_area = soup.select_one(selector)
                if content_area:
                    return content_area.get_text(strip=True)
            
            # 본문 영역을 찾지 못한 경우 전체 텍스트 반환
            return soup.get_text()
            
        except Exception as e:
            self.logger.error(f"포스트 내용 가져오기 중 오류 발생: {str(e)}")
            return ""
    
    def parse_recipe_from_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """블로그 콘텐츠에서 레시피 정보 추출"""
        if not content:
            return {}
            
        title = content.get('title', '')
        description = content.get('description', '')
        full_content = content.get('content', '')
        
        # 재료 추출
        ingredients = self._extract_ingredients(full_content)
        
        # 조리 단계 추출
        steps = self._extract_steps(full_content)
        
        # 메타데이터 추출
        metadata = self._extract_metadata(full_content)
        
        return {
            'title': title,
            'ingredients': ingredients,
            'steps': steps,
            'metadata': metadata,
            'source': content.get('link', ''),
            'author': content.get('bloggerName', '')
        }
    
    def _extract_ingredients(self, content: str) -> List[Dict[str, Any]]:
        """블로그 콘텐츠에서 재료 목록 추출"""
        ingredients = []
        
        # 재료 섹션 패턴 찾기
        ingredient_patterns = [
            r'(?:재료|준비물)[^\n]*\n(.*?)(?:만드는 법|조리 방법|레시피|요리 방법)',
            r'(?:재료|준비물)[^\n]*\n(.*?)(?:\d+\.|1\.|\[|\(1\))'
        ]
        
        for pattern in ingredient_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                ingredient_text = match.group(1).strip()
                
                # 줄 단위로 분리
                lines = [line.strip() for line in ingredient_text.split('\n') if line.strip()]
                
                for line in lines:
                    # 재료와 양 분리 (여러 패턴 시도)
                    name, amount = self._parse_ingredient_line(line)
                    
                    if name:
                        ingredients.append({
                            'name': name,
                            'amount': {
                                'original': amount,
                                'value': self._extract_numeric_value(amount),
                                'unit': self._extract_unit(amount)
                            },
                            'group': '주재료'
                        })
                
                break
        
        return ingredients
    
    def _parse_ingredient_line(self, line: str) -> tuple:
        """재료 라인에서 재료명과 양 추출"""
        # 패턴 1: "재료: 양" 형태
        if ':' in line:
            parts = line.split(':', 1)
            return parts[0].strip(), parts[1].strip()
        
        # 패턴 2: "재료 양" 형태
        match = re.match(r'([가-힣a-zA-Z]+)\s+(\d+[가-힣a-zA-Z\s]*)', line)
        if match:
            return match.group(1), match.group(2)
        
        # 패턴 3: 괄호 사용 "재료(양)" 형태
        match = re.match(r'([가-힣a-zA-Z]+)\(([^)]+)\)', line)
        if match:
            return match.group(1), match.group(2)
        
        # 그 외 경우 라인 전체를 재료명으로 처리
        return line, '적당량'
    
    def _extract_numeric_value(self, amount: str) -> Optional[float]:
        """양에서 숫자 값 추출"""
        if not amount:
            return None
            
        # 숫자 추출
        match = re.search(r'(\d+(?:\.\d+)?)', amount)
        if match:
            return float(match.group(1))
        
        # 분수 처리
        match = re.search(r'(\d+)/(\d+)', amount)
        if match:
            return float(int(match.group(1)) / int(match.group(2)))
        
        return None
    
    def _extract_unit(self, amount: str) -> Optional[str]:
        """양에서 단위 추출"""
        if not amount:
            return None
            
        # 일반적인 단위 목록
        units = ['g', 'kg', 'ml', 'l', '컵', '큰술', '작은술', '개', '마리', '조각', '장', '포기']
        
        for unit in units:
            if unit in amount:
                return unit
        
        return None
    
    def _extract_steps(self, content: str) -> List[Dict[str, str]]:
        """블로그 콘텐츠에서 조리 단계 추출"""
        steps = []
        
        # 조리 방법 섹션 찾기
        step_section_patterns = [
            r'(?:만드는 법|조리 방법|레시피|요리 방법)[^\n]*\n(.*?)(?:팁|참고|마무리|완성|$)',
            r'(?:\d+\.|1\.|\[|\(1\))(.*?)(?:$)'
        ]
        
        for pattern in step_section_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                step_text = match.group(1).strip()
                
                # 단계별로 분리
                # 1. 번호 형식으로 분리 시도
                step_matches = re.findall(r'(?:\d+\.|STEP\s*\d+|\[\d+\]|\(\d+\))(.*?)(?=\d+\.|STEP\s*\d+|\[\d+\]|\(\d+\)|$)', step_text, re.DOTALL)
                
                if step_matches:
                    for idx, step_match in enumerate(step_matches, 1):
                        step_desc = step_match.strip()
                        if step_desc:
                            steps.append({
                                'step_num': idx,
                                'description': step_desc
                            })
                else:
                    # 2. 줄 단위로 분리
                    lines = [line.strip() for line in step_text.split('\n') if line.strip() and len(line.strip()) > 5]
                    for idx, line in enumerate(lines, 1):
                        steps.append({
                            'step_num': idx,
                            'description': line
                        })
                
                break
        
        return steps
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """블로그 콘텐츠에서 메타데이터 추출"""
        metadata = {
            'time': {'original': '', 'minutes': None},
            'difficulty': {'original': '초급', 'level': 1},
            'servings': {'original': '1인분', 'servings': 1}
        }
        
        # 조리 시간 추출
        time_match = re.search(r'(?:조리|준비)?\s*시간\s*:?\s*(\d+(?:\s*~\s*\d+)?\s*분|\d+시간(?:\s*\d+분)?)', content)
        if time_match:
            time_str = time_match.group(1)
            metadata['time']['original'] = time_str
            
            # 시간 값 추출
            if '시간' in time_str:
                hours_match = re.search(r'(\d+)시간', time_str)
                minutes_match = re.search(r'(\d+)분', time_str)
                
                minutes = 0
                if hours_match:
                    minutes += int(hours_match.group(1)) * 60
                if minutes_match:
                    minutes += int(minutes_match.group(1))
                
                metadata['time']['minutes'] = minutes
            else:
                minutes_match = re.search(r'(\d+)', time_str)
                if minutes_match:
                    metadata['time']['minutes'] = int(minutes_match.group(1))
        
        # 난이도 추출
        difficulty_match = re.search(r'난이도\s*:?\s*(초급|중급|고급|쉬움|보통|어려움)', content)
        if difficulty_match:
            difficulty = difficulty_match.group(1)
            metadata['difficulty']['original'] = difficulty
            
            # 난이도 수준 매핑
            difficulty_map = {'초급': 1, '쉬움': 1, '보통': 2, '중급': 2, '고급': 3, '어려움': 3}
            metadata['difficulty']['level'] = difficulty_map.get(difficulty, 1)
        
        # 인분 수 추출
        servings_match = re.search(r'(?:인분|분량|양)\s*:?\s*(\d+)(?:인분|명|개|servings|portions)?', content)
        if servings_match:
            servings = int(servings_match.group(1))
            metadata['servings']['original'] = f"{servings}인분"
            metadata['servings']['servings'] = servings
        
        return metadata
    
    def _get_direct_post_content(self, blog_id: str, log_no: str) -> Optional[str]:
        """API 대신 직접 포스트 접근"""
        try:
            # PC 버전과 모바일 버전 URL
            urls = [
                f"https://blog.naver.com/{blog_id}/{log_no}",
                f"https://m.blog.naver.com/{blog_id}/{log_no}",
                f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            ]
            
            # 세션 설정
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://m.search.naver.com/'
            })
            
            # 각 URL 시도
            for url in urls:
                try:
                    response = session.get(url, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 모바일 버전 파싱
                        if 'm.blog.naver.com' in url:
                            content_div = soup.select_one('div.se-main-container, div.post_ct')
                            if content_div:
                                return content_div.get_text(strip=True)
                        
                        # PC 버전 파싱 (iframe 처리)
                        else:
                            iframe = soup.select_one('iframe#mainFrame')
                            if iframe and 'src' in iframe.attrs:
                                iframe_url = f"https://blog.naver.com{iframe['src']}"
                                iframe_response = session.get(iframe_url, timeout=10)
                                if iframe_response.status_code == 200:
                                    iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                                    content_div = iframe_soup.select_one('div.se-main-container')
                                    if content_div:
                                        return content_div.get_text(strip=True)
                except Exception as req_error:
                    self.logger.debug(f"URL {url} 접근 실패: {str(req_error)}")
                    continue
                    
            return None
            
        except Exception as e:
            self.logger.error(f"직접 포스트 접근 중 오류: {str(e)}")
            return None
        
    def _fallback_search(self, blog_id: str, log_no: str) -> Optional[Dict[str, Any]]:
        """API 검색 실패시 대체 검색 방법"""
        try:
            # 1. 블로그 ID만으로 검색
            api_url = f"https://openapi.naver.com/v1/search/blog.json?query={blog_id}&display=100"
            
            response = requests.get(api_url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                
                # 모든 결과에서 logNo 포함된 항목 찾기
                for item in data.get('items', []):
                    if log_no in item.get('link', ''):
                        post_url = item.get('link', '')
                        post_content = self._get_post_content(post_url)
                        
                        if not post_content:
                            # 직접 접근 시도
                            post_content = self._get_direct_post_content(blog_id, log_no)
                        
                        return {
                            'title': item.get('title', '').replace('<b>', '').replace('</b>', ''),
                            'description': item.get('description', '').replace('<b>', '').replace('</b>', ''),
                            'link': post_url,
                            'bloggerName': item.get('bloggername', ''),
                            'content': post_content or "내용을 가져올 수 없습니다"
                        }
            
            # 2. 직접 접근으로 내용 가져오기
            content = self._get_direct_post_content(blog_id, log_no)
            if content:
                # 내용으로 제목 추출 (첫 줄 또는 처음 나오는 제목 태그)
                title = content.split('\n')[0][:50] if '\n' in content else f"{blog_id}의 블로그 포스트"
                
                return {
                    'title': title,
                    'description': content[:150] + "...",
                    'link': f"https://blog.naver.com/{blog_id}/{log_no}",
                    'bloggerName': blog_id,
                    'content': content
                }
                
            return None
            
        except Exception as e:
            self.logger.error(f"폴백 검색 중 오류: {str(e)}")
            return None