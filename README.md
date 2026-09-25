# Python AI Util

자주 쓰는 텍스트 추출, PDF 변환, 유튜브 다운로드, 이미지 생성을 웹 화면에서 처리하는 개인용
FastAPI 앱입니다. 본인 전용(로그인·과금 없음)이며 Contabo VPS의 Docker에서
`tools.manizu.blog`로 운영하고, Nginx Proxy Manager의 Basic Auth로 본인 외 접근을
막습니다. AI 기능은 이미지 생성 프롬프트 번역(OpenAI)에만 쓰고 나머지는 범위에서
제외했습니다(`TASKS.md` "프로젝트 범위에서 제외").

## 기능

**텍스트 추출기**

- TXT·Markdown, PDF, DOCX 텍스트 추출
- 이미지 OCR(한국어+영어, Tesseract): `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tif`, `.tiff`

**PDF 변환기**

- PDF → 페이지 이미지 ZIP
- PDF → Word(텍스트만 옮기며 레이아웃·표·이미지는 유지되지 않음)
- PDF → Excel(페이지·줄 단위 텍스트 목록)
- PDF 병합(여러 파일 누적 선택), 페이지 범위 분할, 압축
- TXT, Markdown, DOCX, 이미지 → PDF

**유튜브 도구**

- 공개된 단일 영상 다운로드(`.mp4`, `.webm`, `.mkv`)와 MP3 음원 추출
- 한국어 또는 영어 자막 텍스트 추출(`.txt`)

본인이 저장할 권한이 있는 콘텐츠에만 사용하세요. 실제 다운로드 가능 여부는 영상 공개
범위, 지역·연령 제한 및 네트워크 상태에 따라 달라집니다.

**이미지 생성**

- 한국어 프롬프트를 OpenAI로 영어 문장 프롬프트로 번역(확인·수정 후 생성, 영어 직접 입력 가능)
- 집 Windows PC의 ComfyUI(Z-Image Turbo)로 세로·가로·정사각 PNG 1장 생성, 미리보기와 다운로드

## 구조

```text
[브라우저] ── HTTPS + Basic Auth ──▶ [Nginx Proxy Manager] ── tools.manizu.blog
                                            │
                                            ▼
                                   [FastAPI 컨테이너] ── 변환·추출 처리, 결과 파일 반환
                                            │
                                            ├─ 유튜브 요청만 ── Tailscale ──▶ [집 Mac mini SOCKS5 프록시] ──▶ YouTube
                                            └─ 이미지 생성만 ── Tailscale ──▶ [집 Windows PC ComfyUI :8188]
```

유튜브는 데이터센터 IP를 차단하므로 유튜브 요청만 가정용 회선을 거칩니다
([`DEPLOYMENT.md`](DEPLOYMENT.md) 11절).
이미지 생성은 GPU가 있는 집 Windows PC의 ComfyUI를 Tailscale로만 호출합니다
([`DEPLOYMENT.md`](DEPLOYMENT.md) 12절). PC가 꺼져 있으면 이미지 생성만 실패합니다.

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.12, FastAPI |
| 프론트엔드 | 단순 HTML/CSS/JavaScript |
| 파일 처리 | PyMuPDF, python-docx, openpyxl, reportlab, Pillow, Tesseract OCR |
| 유튜브 | yt-dlp, Deno(JS 런타임), ffmpeg |
| 이미지 생성 | OpenAI API(번역), ComfyUI(Z-Image Turbo GGUF), httpx |
| 인프라 | Docker Compose, Nginx Proxy Manager, Let's Encrypt, Tailscale |

```text
app/              FastAPI 앱과 설정
app/routers/      텍스트, PDF, YouTube, 이미지 생성, 결과 다운로드 API 라우터
app/comfyui_workflows/  ComfyUI API 형식 워크플로 템플릿
app/services/     파일 저장, 변환, 추출 및 정리 기능
static/           프론트엔드 정적 자산
tests/            pytest 테스트
```

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

유튜브 다운로드에는 `ffmpeg`, `ffprobe`와 JS 런타임 Deno 2.3 이상이 필요합니다.
Docker 이미지에는 필요한 도구가 모두 포함되어 있습니다. 로컬에서 직접 실행할 때는
`brew install deno` 등으로 Deno를 설치하세요. OCR까지 확인하려면 Tesseract가 포함된
Docker 실행을 권장합니다.

## Docker 실행

```bash
cp .env.example .env
docker compose up --build
```

- 웹 화면: <http://localhost:8010>
- 상태 확인: <http://localhost:8010/health> → `{"status":"ok"}`

포그라운드 실행은 `Ctrl+C`로 멈추고, 컨테이너와 네트워크까지 정리하려면
`docker compose down`을 실행합니다.

VPS 운영 배포, Nginx Proxy Manager, HTTPS, 업데이트 및 롤백 절차는
[`DEPLOYMENT.md`](DEPLOYMENT.md)를 참고하세요.

## 테스트

```bash
source .venv/bin/activate
pytest
```

2026-09-26 기준 자동 테스트는 101개입니다. 화면에서 확인할 때는 위 "기능"의 항목을
하나씩 실행하고 결과 파일을 내려받아 봅니다.

## 환경 변수

설정 예시는 `.env.example`을 참고하세요. 로컬 설정이 들어 있는 `.env`는 Git에서 제외됩니다.

`APP_ENV=production`(운영 오버라이드 `compose.production.yml`이 지정)이면 FastAPI가 자동으로
만드는 API 문서 화면(`/docs`, `/redoc`, `/openapi.json`)을 끕니다. 로컬 개발에서는 그대로 열립니다.

업로드 파일과 생성 결과는 각각 `uploads/`, `results/`에 저장되며 저장소에 커밋되지 않습니다.
기본 보관 기간은 24시간이며, 앱 시작 시와 실행 중 60분 간격으로 만료 파일을 정리합니다.
보관 기간은 `UPLOAD_RETENTION_HOURS`, `RESULT_RETENTION_HOURS`, 정리 주기는
`CLEANUP_INTERVAL_MINUTES`로 변경할 수 있습니다.
유튜브 결과 크기와 영상 길이 제한은 `YOUTUBE_MAX_DOWNLOAD_MB`,
`YOUTUBE_MAX_DURATION_SECONDS`로 설정합니다.
VPS처럼 데이터센터 IP에서 유튜브 접근이 차단되는 환경에서는 `YOUTUBE_PROXY`에
가정용 회선의 SOCKS5 프록시 주소를 지정합니다. 설정 방법은
[`DEPLOYMENT.md`](DEPLOYMENT.md) 11절을 참고하세요.

이미지 생성에는 `OPENAI_API_KEY`(ChatGPT 구독과 별개인 OpenAI API 키), `OPENAI_MODEL`(기본
`gpt-6-luna`), Windows ComfyUI 주소 `COMFYUI_URL`(예: `http://<windows-tailscale-ip>:8188`)과
생성 대기 한도 `COMFYUI_TIMEOUT_SECONDS`(기본 300초)가 필요합니다. 비워 두면 해당 버튼이
원인을 안내하는 오류를 냅니다. 설정 방법은 [`DEPLOYMENT.md`](DEPLOYMENT.md) 12절을 참고하세요.

## 문서

- [`TASKS.md`](TASKS.md): 작업 체크리스트, 남은 작업, 검증 기록
- [`DEPLOYMENT.md`](DEPLOYMENT.md): VPS 배포·운영 절차
- [`AGENTS.md`](AGENTS.md): 코딩 에이전트용 저장소 지침
