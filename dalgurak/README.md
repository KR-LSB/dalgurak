# Dalgurak (달그락) - AI Cooking Assistant

## 프로젝트 소개
요리 초보자들을 위한 AI 기반 요리 어시스턴트 애플리케이션입니다. 
실시간 요리 가이드와 음성 안내를 통해 누구나 쉽게 요리할 수 있도록 도와줍니다.

## 기술 스택
- Frontend: React
- Backend: Spring Framework
- AI/ML: Langchain
- Database: [DB 추가 예정]

## 프로젝트 구조
```
dalgurak/
├── frontend/          # React 프로젝트
├── backend/           # Spring 프로젝트
├── ai/                # AI 관련 코드
├── docs/              # 문서
└── README.md
```

## 개발 가이드라인

### Branch 전략
- `main`: 프로덕션 브랜치
- `develop`: 개발 브랜치
- `feature/*`: 기능 개발 브랜치
- `hotfix/*`: 긴급 수정 브랜치

### Commit Convention
```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 코드
chore: 기타 변경사항
```

### Pull Request 프로세스
1. 기능 개발은 `feature/` 브랜치에서 진행
2. 개발 완료 후 `develop` 브랜치로 PR 생성
3. 코드 리뷰 후 승인 시 머지
4. 릴리즈 준비가 완료되면 `main` 브랜치로 머지

## 설치 및 실행
[추후 추가 예정]

## 팀원
- 이승병 (조장)
- 박찬수
- 심현채
- 김진아

