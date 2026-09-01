# Repository Guidelines

## 프로젝트 구조 및 모듈 구성

이 저장소는 개인용 Python + AI 유틸리티 웹 앱을 준비하는 작업 공간입니다. 현재 핵심 문서는 `python-AI-유틸리티웹_개발계획서.md`이며, 작업 체크리스트는 `TASKS.md`에 있습니다. 화면 참고 이미지는 루트의 `MacBook Air - 1.png`처럼 관리합니다.

현재 구조는 아래 기준을 따릅니다.

- `app/`: FastAPI 앱 코드, 라우터, 서비스, 설정 파일
- `app/services/`: 업로드 저장, 텍스트 추출, 파일 정리 같은 처리 로직
- `tests/`: `app/` 구조를 따라가는 pytest 테스트
- `static/`: 단순 HTML, CSS, JavaScript 자산
- `docker-compose.yml`: 로컬 및 VPS 실행용 컨테이너 구성
- `.env.example`: 비밀값을 제외한 환경 변수 예시

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

가능하면 Python 3.12 이상을 사용합니다. PEP 8, 4칸 들여쓰기, 공개 함수의 타입 힌트를 따르세요. 모듈, 함수, 변수, 테스트 파일은 `snake_case`를 사용하고 클래스는 `PascalCase`를 사용합니다. FastAPI 라우터는 얇게 유지하고 변환, OCR, AI 연동 같은 처리는 `app/services/pdf_converter.py`와 같은 서비스 모듈로 분리하세요.

## 테스트 지침

테스트 프레임워크는 `pytest`를 사용합니다. 테스트 파일은 `test_<module>.py`, 테스트 함수는 `test_<behavior>()` 형식으로 작성하세요. 파일 변환, OCR, AI 워크플로우 경계, 지원하지 않는 파일 형식, `ffmpeg` 같은 외부 바이너리 누락 상황을 우선 검증합니다.

## 커밋 및 풀 리퀘스트 지침

현재 디렉터리는 Git 저장소가 아니므로 기존 커밋 규칙은 확인할 수 없습니다. Git을 초기화한 뒤에는 `Add FastAPI health endpoint`, `Document Docker setup`처럼 짧은 명령형 커밋 메시지를 사용하세요. 풀 리퀘스트에는 변경 요약, 테스트 결과, 관련 이슈 또는 작업 링크, UI 변경 시 스크린샷을 포함합니다.

## 보안 및 설정 팁

API 키, 업로드 파일, 생성된 결과 파일은 커밋하지 마세요. 로컬 비밀값은 `.env`에 두고, 공유 가능한 예시는 `.env.example`에만 작성합니다. 배포 시에는 개인용 도구라는 전제에 맞게 Basic Auth, IP 제한, 또는 별도 접근 제어를 적용하세요.
