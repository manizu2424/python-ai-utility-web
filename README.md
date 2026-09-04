# Python AI 유틸리티 웹

개인용 파일 변환, 텍스트 추출, OCR 및 미디어 다운로드 기능을 제공하기 위한 FastAPI 웹 앱입니다.

현재 텍스트 추출, PDF 변환, 단일 유튜브 영상·MP3 다운로드와 자막 텍스트
추출을 지원합니다.

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

유튜브 다운로드에는 `ffmpeg`, `ffprobe`가 필요합니다. Docker 이미지에는 필요한 도구와
YouTube 추출용 Node.js가 포함되어 있습니다. 공개된 단일 영상 중 본인이 저장할 권한이
있는 콘텐츠에만 사용하세요.

## Docker 실행

```bash
cp .env.example .env
docker compose up --build
```

기본 호스트 포트는 `8010`입니다.

VPS 운영 배포, Nginx Proxy Manager, HTTPS, 업데이트 및 롤백 절차는
[`DEPLOYMENT.md`](DEPLOYMENT.md)를 참고하세요.

## 테스트

```bash
pytest
```

화면별 수동 테스트 방법은 [`TESTING_GUIDE.md`](TESTING_GUIDE.md)를 참고하세요.

## 환경 변수

설정 예시는 `.env.example`을 참고하세요. 로컬 설정이 들어 있는 `.env`는 Git에서 제외됩니다.

업로드 파일과 생성 결과는 각각 `uploads/`, `results/`에 저장되며 저장소에 커밋되지 않습니다.
기본 보관 기간은 24시간이며, 앱 시작 시와 실행 중 60분 간격으로 만료 파일을 정리합니다.
보관 기간은 `UPLOAD_RETENTION_HOURS`, `RESULT_RETENTION_HOURS`, 정리 주기는
`CLEANUP_INTERVAL_MINUTES`로 변경할 수 있습니다.
유튜브 결과 크기와 영상 길이 제한은 `YOUTUBE_MAX_DOWNLOAD_MB`,
`YOUTUBE_MAX_DURATION_SECONDS`로 설정합니다.

## 프로젝트 구조

```text
app/              FastAPI 앱과 서비스 로직
app/services/     파일 저장, 변환, 추출 및 정리 기능
static/           프론트엔드 정적 자산
tests/            pytest 테스트
```

개발 계획은 `python-AI-유틸리티웹_개발계획서.md`, 작업 현황은 `TASKS.md`에서 확인할 수 있습니다.
