# Repository Guidelines

## 프로젝트 구조 및 모듈 구성

이 저장소는 개인용 유틸리티 웹 앱 Python AI Util(텍스트 추출, PDF 변환, 유튜브 다운로드)이며 `tools.manizu.blog`에서 운영 중입니다. 개요·기능·실행·테스트는 `README.md`, 작업 체크리스트는 `TASKS.md`, 배포·운영 절차는 `DEPLOYMENT.md`에 있습니다. 문서를 새로 늘리기보다 이 세 문서에 이어서 적습니다. 이름에 AI가 들어가지만 AI 기능은 프로젝트 범위에서 제외되었습니다.

현재 구조는 아래 기준을 따릅니다.

- `app/`: FastAPI 앱 진입점과 설정 파일
- `app/routers/`: 텍스트, PDF, YouTube, 결과 다운로드 API 라우터
- `app/services/`: 업로드 저장, 텍스트 추출, PDF 변환, 유튜브 다운로드, 파일 정리 같은 처리 로직
- `tests/`: `app/` 구조를 따라가는 pytest 테스트
- `static/`: 단순 HTML, CSS, JavaScript 자산
- `docker-compose.yml`: 로컬 및 VPS 실행용 컨테이너 구성
- `compose.production.yml`: 운영 오버라이드(자원 제한, NPM 공유 네트워크)
- `.env.example`: 비밀값을 제외한 환경 변수 예시
- `docs/reviews/`: 문서 검토 보고서(운영 보안 정보가 담길 수 있어 로컬 전용, Git 제외)

## 빌드, 테스트, 개발 명령

기본 FastAPI 앱이 추가되어 있습니다. 다음 명령을 기본으로 사용하세요.

- `python -m venv .venv`: 로컬 가상환경 생성
- `source .venv/bin/activate`: macOS/Linux에서 가상환경 활성화
- `pip install -r requirements.txt`: 의존성 설치
- `uvicorn app.main:app --reload --port 8010`: 개발 서버 실행
- `pytest`: 테스트 실행
- `docker compose up --build`: 컨테이너 빌드 및 로컬 실행. 기본 호스트 포트는 `8010`입니다.

필수 명령이 추가되면 `README.md` 또는 이 문서에 함께 기록하세요.

## 코딩 스타일 및 이름 규칙

가능하면 Python 3.12 이상을 사용합니다. PEP 8, 4칸 들여쓰기, 공개 함수의 타입 힌트를 따르세요. 모듈, 함수, 변수, 테스트 파일은 `snake_case`를 사용하고 클래스는 `PascalCase`를 사용합니다. `static/app.js`나 `static/styles.css`를 바꾸면 `static/index.html`의 `?v=` 값을 함께 올려 브라우저 캐시를 갱신하세요. FastAPI 라우터는 얇게 유지하고 변환, OCR, 유튜브 다운로드 같은 처리는 `app/services/pdf_converter.py`와 같은 서비스 모듈로 분리하세요.

## 테스트 지침

테스트 프레임워크는 `pytest`를 사용합니다. 테스트 파일은 `test_<module>.py`, 테스트 함수는 `test_<behavior>()` 형식으로 작성하세요. 파일 변환, OCR, 유튜브 다운로드, 지원하지 않는 파일 형식, `ffmpeg`·Tesseract 같은 외부 바이너리 누락 상황을 우선 검증합니다. 외부 서비스(yt-dlp 등)는 테스트에서 가짜 객체로 대체합니다.

## 커밋 및 풀 리퀘스트 지침

GitHub 공개 저장소(`manizu2424/python-ai-utility-web`)이며 서버는 `main`을 `git pull`로 배포합니다. 커밋 메시지는 `Add YouTube proxy support for residential routing`처럼 짧은 영어 명령형을 사용하세요. 풀 리퀘스트에는 변경 요약, 테스트 결과, 관련 이슈 또는 작업 링크, UI 변경 시 스크린샷을 포함합니다.

## 보안 및 설정 팁

API 키, 업로드 파일, 생성된 결과 파일, 서버 화면 스크린샷은 커밋하지 마세요. 저장소가 공개 상태이므로 서버 IP, 열린 포트 같은 운영 보안 정보도 커밋하는 문서에 적지 않습니다. 로컬 비밀값은 `.env`에 두고, 공유 가능한 예시는 `.env.example`에만 작성합니다. 운영 도메인은 NPM Access List(Basic Auth)로 보호되어 있습니다(`DEPLOYMENT.md` 5절).
