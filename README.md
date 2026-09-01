# Python AI 유틸리티 웹

개인용 파일 변환, 텍스트 추출, OCR 및 AI 연동 기능을 제공하기 위한 FastAPI 웹 앱입니다.

## 요구 사항

- Python 3.12 이상
- 선택 기능 사용 시 `ffmpeg`, Tesseract OCR 등 외부 도구
- Docker 및 Docker Compose(컨테이너로 실행하는 경우)

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8010
```

브라우저에서 <http://localhost:8010>으로 접속합니다.

## Docker 실행

```bash
cp .env.example .env
docker compose up --build
```

기본 호스트 포트는 `8010`입니다.

## 테스트

```bash
pytest
```

## 환경 변수

설정 예시는 `.env.example`을 참고하세요. 실제 API 키가 들어 있는 `.env`는 Git에서 제외됩니다.

업로드 파일과 생성 결과는 각각 `uploads/`, `results/`에 저장되며 저장소에 커밋되지 않습니다.

## 프로젝트 구조

```text
app/              FastAPI 앱과 서비스 로직
app/services/     파일 저장, 변환, 추출 및 정리 기능
static/           프론트엔드 정적 자산
tests/            pytest 테스트
```

개발 계획은 `python-AI-유틸리티웹_개발계획서.md`, 작업 현황은 `TASKS.md`에서 확인할 수 있습니다.
