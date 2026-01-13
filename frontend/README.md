<div align="center">

# 🥄 달그락 (Dalgurak)

### AI 기반 스마트 요리 어시스턴트

[![React](https://img.shields.io/badge/React-18.2.0-61DAFB?style=flat-square&logo=react&logoColor=white)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-4.5.0-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Demo](https://img.shields.io/badge/🚀_Live-Demo-FF6B6B?style=flat-square)](https://your-demo-link.com)

<p align="center">
  <strong>자연어 대화와 음성 인식으로 누구나 쉽게 요리하는 AI 요리 도우미</strong>
</p>

[Features](#-주요-기능) • [Tech Stack](#-기술-스택) • [Getting Started](#-설치-및-실행) • [Screenshots](#-스크린샷) • [Architecture](#-폴더-구조)

</div>

---

## 📖 프로젝트 개요

**달그락(Dalgurak)** 은 RAG(Retrieval-Augmented Generation) 기술을 활용한 AI 기반 한식 요리 추천 및 가이드 시스템입니다.

### 🎯 해결하는 문제

- 🍳 **요리 초보자의 어려움**: 레시피를 보며 단계별로 요리하기 어려운 사용자들을 위한 실시간 음성 가이드 제공
- 🔍 **레시피 검색의 한계**: 단순 키워드가 아닌 자연어 대화로 원하는 요리를 쉽게 찾기
- ⏱️ **조리 시간 관리**: 각 조리 단계별 자동 타이머로 완벽한 요리 타이밍 지원
- 🎙️ **핸즈프리 요리**: 요리 중 손을 쓰기 어려운 상황에서 음성으로 AI와 소통

### ✨ 핵심 가치

> "말로 묻고, 귀로 듣고, 맛있게 요리하세요"

---

## 🚀 주요 기능

### 💬 AI 채팅 인터페이스
- 자연어 기반 레시피 검색 및 추천
- 실시간 요리 질문 응답
- 컨텍스트 기반 대화 유지

### 🎤 음성 인식 (Voice Recognition)
- Web Speech API 기반 한국어 음성 인식
- 핸즈프리 요리 지원
- 실시간 음성→텍스트 변환

### 📋 단계별 요리 가이드
- 레시피 단계별 상세 안내
- 진행률 시각화
- 이전/다음 단계 네비게이션

### ⏱️ 스마트 타이머
- 단계별 자동 타이머 설정
- 원형 프로그레스 시각화
- 알림 사운드 및 진동 알림

### 🌙 다크 모드
- 시스템 테마 연동
- 눈의 피로 감소
- 저조도 환경 최적화

### 📝 커뮤니티 게시판
- 레시피 공유 및 리뷰
- 댓글 및 좋아요 기능
- 이미지 업로드 지원

---

## 🛠 기술 스택

<table>
<tr>
<td align="center" width="96">
<img src="https://skillicons.dev/icons?i=react" width="48" height="48" alt="React" />
<br>React 18
</td>
<td align="center" width="96">
<img src="https://skillicons.dev/icons?i=vite" width="48" height="48" alt="Vite" />
<br>Vite
</td>
<td align="center" width="96">
<img src="https://skillicons.dev/icons?i=tailwind" width="48" height="48" alt="Tailwind" />
<br>Tailwind CSS
</td>
<td align="center" width="96">
<img src="https://skillicons.dev/icons?i=js" width="48" height="48" alt="JavaScript" />
<br>JavaScript
</td>
</tr>
</table>

### Frontend Core
| 기술 | 버전 | 용도 |
|------|------|------|
| **React** | 18.2.0 | UI 컴포넌트 라이브러리 |
| **Vite** | 4.5.0 | 빌드 도구 및 개발 서버 |
| **React Router DOM** | 6.22.3 | 클라이언트 사이드 라우팅 |

### State Management & Styling
| 기술 | 버전 | 용도 |
|------|------|------|
| **Recoil** | 0.7.7 | 전역 상태 관리 |
| **Tailwind CSS** | 3.4.17 | 유틸리티 기반 스타일링 |
| **Framer Motion** | 12.4.7 | 애니메이션 및 트랜지션 |

### Utilities
| 기술 | 버전 | 용도 |
|------|------|------|
| **Axios** | 1.7.9 | HTTP 클라이언트 |
| **Lucide React** | 0.471.1 | 아이콘 라이브러리 |
| **Web Speech API** | Native | 음성 인식 |

---

## 📦 설치 및 실행

### Prerequisites
- Node.js 18.0.0 이상
- npm 또는 yarn

### Installation

```bash
# 저장소 클론
git clone https://github.com/KR-LSB/dalgurak.git

# 프론트엔드 디렉토리 이동
cd dalgurak/frontend/my-app-main

# 의존성 설치
npm install
```

### Environment Setup

```bash
# 환경변수 파일 생성
cp .env.example .env

# .env 파일 편집
VITE_API_BASE_URL=http://localhost:8000/api
```

### Development

```bash
# 개발 서버 실행
npm run dev

# 브라우저에서 http://localhost:5173 접속
```

### Production Build

```bash
# 프로덕션 빌드
npm run build

# 빌드 미리보기
npm run preview
```

### Docker (Optional)

```bash
# Docker 이미지 빌드
docker build -t dalgurak-frontend .

# 컨테이너 실행
docker run -p 80:80 dalgurak-frontend
```

---

## 📸 스크린샷

### 메인 화면
> AI 채팅 인터페이스와 빠른 추천 기능
![Main Screen](./screenshots/main.png)

### 요리 가이드 모드
> 단계별 가이드와 실시간 타이머
![Cooking Guide](./screenshots/cooking-guide.png)

### 음성 인식
> 핸즈프리 음성 명령 지원
![Voice Recognition](./screenshots/voice.png)

### 다크 모드
> 저조도 환경 최적화
![Dark Mode](./screenshots/dark-mode.png)

---

## 📂 폴더 구조

```
frontend/my-app-main/
├── src/
│   ├── api/                    # API 서비스 및 엔드포인트
│   │   ├── apiServices.js
│   │   └── endpoints.js
│   │
│   ├── components/             # 재사용 가능한 UI 컴포넌트
│   │   ├── animation/          # 애니메이션 컴포넌트
│   │   ├── chat/               # 채팅 관련 컴포넌트
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── ChatMessage.jsx
│   │   │   └── QuickSuggestions.jsx
│   │   ├── common/             # 공통 UI 컴포넌트
│   │   ├── recipe/             # 레시피 관련 컴포넌트
│   │   └── timer/              # 타이머 컴포넌트
│   │
│   ├── features/               # 기능별 모듈 (Feature-based)
│   │   ├── auth/               # 인증 기능
│   │   │   ├── api/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── utils/
│   │   ├── board/              # 게시판 기능
│   │   ├── chat/               # 채팅 기능
│   │   ├── cooking/            # 요리 가이드 기능
│   │   ├── home/               # 홈 화면 기능
│   │   └── recipe/             # 레시피 기능
│   │
│   ├── hooks/                  # 커스텀 훅
│   │   ├── useChatBot.js       # 채팅봇 로직
│   │   ├── useRecipeTimer.js   # 타이머 로직
│   │   └── useVoiceRecognition.jsx  # 음성 인식
│   │
│   ├── pages/                  # 페이지 컴포넌트
│   │   ├── Home.jsx
│   │   ├── CookingGuide.jsx
│   │   ├── Favorites.jsx
│   │   └── ...
│   │
│   ├── store/                  # Recoil 상태 관리
│   │   ├── atoms.js
│   │   └── boardState.js
│   │
│   └── utils/                  # 유틸리티 함수
│
├── .env                        # 환경변수
├── Dockerfile                  # Docker 설정
├── nginx.conf                  # Nginx 설정
├── package.json
├── tailwind.config.cjs
└── vite.config.js
```

---

## 🔗 관련 저장소

| 저장소 | 설명 |
|--------|------|
| [dalgurak-backend](https://github.com/KR-LSB/dalgurak) | FastAPI 백엔드 & RAG 시스템 |

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by [KR-LSB](https://github.com/KR-LSB)**

⭐ Star this repo if you find it helpful!

</div>