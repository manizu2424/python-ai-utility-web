# 개발 작업 목록

## 남은 작업 (2026-09-25 기준)

Phase 0~3은 모두 완료했다. 남은 작업은 다음 네 가지이며 위에서부터 진행한다.

1. 운영 환경 API 문서 화면(`/docs`, `/redoc`) 비활성화 여부 결정 (아래 "문서 검토 후속 조치")
2. 운영 로그 개인정보 점검 (운영 및 유지보수 작업)
3. OCR 전처리 개선과 품질 회귀 테스트 (테스트 작업, "OCR 현황과 개선 메모")
4. VPS 접속 정보와 운영 계정 정리 (Phase 0)

## Phase 0. 인프라 및 프로젝트 골격

- [ ] Contabo VPS 접속 정보와 운영 계정 정리
- [x] VPS에 Docker 및 Docker Compose 설치 여부 확인
- [x] Nginx Proxy Manager 컨테이너 구성
- [x] `tools.manizu.blog` 서브도메인 DNS 연결 (계획의 manizu.kr에서 변경)
- [x] Let's Encrypt HTTPS 인증서 적용
- [x] 개인 접근 제한 적용: NPM Access List Basic Auth (2026-09-25)
- [x] FastAPI 기본 프로젝트 생성
  - [x] `app/main.py` 생성
  - [x] `/health` 상태 확인 API 추가
  - [x] 기본 HTML 업로드 화면 추가
- [x] Docker 실행 파일 추가
  - [x] `Dockerfile`
  - [x] `docker-compose.yml`
  - [x] `.env.example`

완료 기준:

- 로컬: `docker compose up --build`로 FastAPI 앱이 실행되고 `/health`가 정상 응답한다. `8010` 포트에서 확인 완료.
- 운영: `https://tools.manizu.blog`에서 HTTPS와 접근 제한이 적용된 상태로 `/health`가 정상 응답한다.

현재 상태: 완료(VPS 계정 정리 제외). 2026-09-04 VPS(`/home/docker/pytool`) 배포, 2026-09-25 접근 제한 적용.

## Phase 1. 텍스트 추출기 및 PDF 변환기

- [x] 업로드 파일 저장 위치와 자동 삭제 정책 정의
- [x] 지원 파일 형식 제한 추가: 이미지, PDF, 문서
- [x] 텍스트 추출 기능 구현
  - [x] PDF 텍스트 추출
  - [x] 이미지 OCR 처리
  - [x] 문서 파일 텍스트 추출
- [x] PDF 변환 기능 구현
  - [x] PDF를 이미지로 변환
  - [x] PDF를 Word 또는 Excel로 변환
  - [x] PDF 병합
  - [x] PDF 분할
  - [x] PDF 압축
  - [x] 텍스트, DOCX, 이미지 파일을 PDF로 변환
- [x] 결과 파일 다운로드 API 추가
- [x] 실패 케이스 처리
  - [x] 지원하지 않는 파일 형식
  - [x] 확장자와 실제 파일 내용 불일치
  - [x] 파일 크기 초과
  - [x] 변환 실패

완료 기준: AI 기능 없이 업로드, 변환, 추출, 다운로드 흐름이 브라우저에서 동작한다.

현재 상태: 완료. 텍스트 추출, PDF 변환, 다중 PDF 병합, 다른 파일의 PDF 변환, 결과 다운로드 및 초기화 흐름을 구현하고 로컬 테스트로 검증했다. 병합 파일 다중 선택은 2026-09-25 브라우저 회귀 테스트로 확인했고, 이때 발견한 삭제 후 개수 문구 오류도 수정했다.

## Phase 2. 유튜브 다운로드 및 자막 추출

- [x] Docker 이미지에 `ffmpeg` 설치 기반 추가
- [x] `yt-dlp` 실행 환경 확인
- [x] 유튜브 URL 입력 화면 추가
- [x] 영상 다운로드 기능 구현
- [x] 음원 추출 기능 구현
- [x] 한국어·영어 자막 텍스트 추출
- [x] 자막 결과 화면 표시 및 파일 다운로드

완료 기준: 유튜브 URL 입력 후 영상·음원 또는 자막 텍스트 결과를 받을 수 있다.

현재 상태: 완료. 단일 영상·MP3 다운로드와 한국어·영어 자막 추출 및 결과 다운로드를 지원한다. VPS에서는 유튜브가 데이터센터 IP를 차단하므로 가정용 회선 프록시(`DEPLOYMENT.md` 11절)를 거쳐 동작한다(2026-09-25 구성·운영 확인). Mac mini가 꺼져 있거나 로그인 전이면 유튜브 기능이 실패한다.

## Phase 3. 이미지 생성 (Windows ComfyUI 연동)

메뉴에서 한국어 프롬프트를 입력하면 OpenAI로 영어 프롬프트를 만들고, 집 Windows PC의 ComfyUI에서 이미지를 생성해 내려받는다. 텔레그램·n8n은 거치지 않는다. 설계는 2026-09-25에 확정했다.

### 설계 결정

- 흐름: 2단계. [번역]으로 영어 프롬프트를 받아 확인·수정한 뒤 [생성]한다. 영어를 직접 입력하면 번역 없이 생성할 수 있다.
- 번역: OpenAI API(`httpx` 직접 호출, 새 의존성 없음). Z-Image Turbo에 맞춰 태그 나열이 아닌 자연스러운 영어 문장으로 번역하고 설명 없이 결과만 출력하도록 지시한다. ChatGPT 구독과 별개인 API 키·크레딧이 필요하다.
- 연결: VPS 컨테이너 → Tailscale → Windows ComfyUI `:8188`. 포트는 인터넷과 집 LAN에 공개하지 않는다. tailnet 기기 간 접근은 Windows `Tailscale-In` 규칙으로 열려 있어 Tailscale ACL로만 좁힐 수 있다(2026-09-25 확인). 실제 IP는 `.env`에만 둔다.
- 대기 방식: 동기. `POST /api/image/generate` 한 요청이 `/prompt` 제출 → `/history/{prompt_id}` 2초 간격 폴링 → `/view` 다운로드까지 마치고 응답한다. 작업 ID·폴링 API와 WebSocket 진행률은 두지 않는다.
- 워크플로: Z-Image Turbo GGUF(Qwen3-4B 텍스트 인코더, 8 steps, `cfg 1`) API 형식 JSON을 `app/comfyui_workflows/z_image_turbo.json`에 두고 다음 노드만 바꾼다. 노드 번호는 `comfyui_client.py` 상수로 모은다.
  - 노드 2 `text`: 영어 프롬프트
  - 노드 5 `seed`: 요청마다 서버에서 무작위 생성(ComfyUI 화면의 randomize는 API에 적용되지 않음)
  - 노드 8 `width`·`height`: `portrait` 768×1024(기본), `landscape` 1024×768, `square` 1024×1024
  - 부정 프롬프트(노드 7)는 `cfg 1`에서 효과가 없어 화면에 두지 않는다.
  - 출력 노드 10은 `PreviewImage` 그대로 둔다. `/history`의 `filename`·`subfolder`·`type`으로 가져오며 Windows에 이미지가 쌓이지 않는다.
- 저장: 받은 PNG는 `save_result_bytes(..., ".png", ...)`로 `results/`에 저장하고 기존 24시간 정리와 `/api/results/{id}` 다운로드를 그대로 쓴다. `MEDIA_TYPES`에 `.png`를 추가한다.
- 동시 요청 제한과 시간 초과 시 ComfyUI 작업 취소는 두지 않는다(개인용, 대기열은 ComfyUI가 관리).

### 구성 요소

- `app/routers/image.py`
  - `POST /api/image/translate`: 폼 `prompt`(한국어) → `{"prompt_en"}`
  - `POST /api/image/generate`: 폼 `prompt`(영어), `size` → `{"message", "result_id", "download_url", "seed", "width", "height"}`
- `app/services/prompt_translator.py`: `translate_prompt(text, settings) -> str`
- `app/services/comfyui_client.py`: `build_workflow(prompt, width, height, seed) -> dict`, `generate_image(prompt, size, settings) -> GeneratedImage`(PNG 바이트, seed, 크기)
- 설정(`Settings`, `.env.example`): `OPENAI_API_KEY`, `OPENAI_MODEL`(기본 `gpt-6-luna`. 처음 정한 `gpt-5-mini`는 2026-12-11 지원 종료 예정이라 교체), `COMFYUI_URL`(예: `http://<windows-tailscale-ip>:8188`), `COMFYUI_TIMEOUT_SECONDS`(기본 300)
- 화면: "이미지 생성" 메뉴. 한국어 입력 + [번역], 영어 프롬프트(수정 가능) + 크기 선택 + [생성], 결과 미리보기 `<img>` + [다운로드]. `?v=` 갱신.

### 오류 처리

서비스는 `PromptTranslationError`, `ComfyUIError`를 던지고 라우터가 상태 코드로 바꾼다.

| 상황 | 응답 |
|---|---|
| 빈 프롬프트, 2000자 초과(번역·생성 공통), 잘못된 `size` | 422 |
| `OPENAI_API_KEY`·`COMFYUI_URL` 미설정 | 503 |
| ComfyUI 연결 실패(거부·시간 초과): PC 전원, `--listen` 실행, Tailscale 확인 안내 | 503 |
| `/prompt`의 `node_errors`(모델 파일 없음, GGUF 노드 미설치 등) | 502 |
| `/history` 실행 상태 `error` | 502 |
| 대기 한도 초과(Windows 대기열에 작업이 남을 수 있음 안내) | 504 |
| OpenAI 401(키 오류)·429(한도·잔액) 등 | 502 |

### 작업 체크리스트

- [x] 워크플로 템플릿 JSON 추가
- [x] 설정 항목과 `.env.example` 추가
- [x] `comfyui_client.py` 구현과 테스트
- [x] `prompt_translator.py` 구현과 테스트
- [x] `app/routers/image.py` 추가와 앱 등록, `.png` 결과 형식 추가
- [x] "이미지 생성" 화면 추가
- [x] Windows 준비: ComfyUI `--listen` 실행 bat, ComfyUI Python의 `Query User` 허용 규칙 비활성화. tailnet 기기는 Windows의 `Tailscale-In` 규칙으로 접속 가능하며 본인 기기뿐이라 그대로 둔다(제한이 필요하면 Tailscale ACL, `DEPLOYMENT.md` 12.2절)
- [x] 로컬 실제 검증: Mac에서 Tailscale 경유로 1장 생성
- [x] 운영 검증: 컨테이너 안에서 `COMFYUI_URL/system_stats` 응답 확인 후 `tools.manizu.blog`에서 생성·다운로드
- [x] 문서 반영: `README.md`(기능, 구조도, 환경 변수, AI 범위 문구), `DEPLOYMENT.md`(Windows ComfyUI 연결 절, IP는 자리 표시자), `AGENTS.md`(AI 범위 문구)

테스트(외부 호출은 `httpx.MockTransport`로 대체):

- `tests/test_comfyui_client.py`: 노드 값 치환과 원본 템플릿 불변, 정상 흐름(제출 → 미완료 → 완료 → PNG), 연결 실패, `node_errors`, 실행 `error`, 시간 초과(폴링 간격·시계 주입), 설정 누락
- `tests/test_prompt_translator.py`: 정상 번역, 앞뒤 공백·따옴표 제거, 401·429, 키 누락
- `tests/test_config.py`: 새 환경 변수 기본값

완료 기준: `tools.manizu.blog`에서 한국어 프롬프트를 번역·확인한 뒤 생성한 이미지를 미리 보고 내려받을 수 있다. Windows PC나 ComfyUI가 꺼져 있으면 원인을 알 수 있는 오류가 표시된다.

현재 상태: 완료. 2026-09-25 운영 배포 후 `tools.manizu.blog`에서 번역·생성·다운로드를 확인했다. Windows PC나 ComfyUI가 꺼져 있으면 이미지 생성이 실패한다.

후속 개선(선택, 2026-09-25 최종 코드 리뷰에서 보류):

- [ ] ComfyUI에서 작업을 취소(`execution_interrupted`)하면 "알 수 없는 오류" 대신 취소 안내 표시
- [ ] 번역 오류 구분: 응답 시간 초과, 모델의 거절(`refusal`), 길이 제한(`finish_reason: length`)
- [ ] 번역 결과가 2000자를 넘으면 번역 직후 안내(현재는 생성 시 422)
- [ ] Firefox 응답 대기 한도(300초)와 `COMFYUI_TIMEOUT_SECONDS` 기본 300초 충돌 검토
- [ ] `/prompt`·`/view` 응답 지연(`ReadTimeout`)을 "PC 꺼짐"과 구분해 안내

## 프로젝트 범위에서 제외

- 자막 및 추출 텍스트의 AI 요약
- 외부 자동화 Webhook 연동
- 번역, 교정, PDF Q&A, 이미지 설명 등 LLM 기반 기능(예외: Phase 3 이미지 생성 프롬프트 번역에만 OpenAI 사용)
- Excel(XLSX) → PDF 변환
- 레이아웃·표·이미지를 보존하는 PDF ↔ Word/Excel 변환(현재는 텍스트 기반 변환)

## 운영 및 유지보수 작업

- [x] 업로드 파일과 결과 파일 자동 삭제 스케줄 추가
- [x] Docker 로그 순환 보관 정책 정의
- [ ] 운영 로그 개인정보 점검: uvicorn·NPM 접근 로그에 유튜브 URL과 업로드 파일명이 남지 않는지 확인(앱 자체 로깅 없음, 유튜브 URL은 POST 본문으로 전송)
- [x] 백업이 필요한 설정 파일 목록 정리
- [x] VPS 배포 절차 문서화
- [x] 장애 시 재시작 방법 문서화

## 테스트 작업

- [x] `pytest` 기본 설정 추가
- [x] `/health` API 테스트 작성
- [x] 파일 업로드 테스트 작성
- [x] PDF 변환 테스트 작성
- [x] OCR 실패 케이스 테스트 작성
- [x] 유튜브 URL 검증 및 다운로드 서비스 테스트 작성
- [x] Docker 빌드 검증 절차 추가
- [x] PDF 변환 결과 생성, 텍스트 추출(OCR 포함), 주기 파일 정리의 이벤트 루프 비차단 처리 검증
- [x] 텍스트 파일 업로드 및 결과 다운로드 검증
- [x] PDF 2개 이상 병합 API 검증
- [x] PDF 분할 페이지 범위 검증
- [x] TXT 및 이미지 파일의 PDF 변환 검증
- [x] 브라우저에서 병합 파일을 여러 번 선택하는 회귀 테스트 (2026-09-25, Playwright/Chromium: 누적 선택, 중복 방지, PDF 외 파일 제외, 개별 삭제·번호 재정렬, 비우기, 2개 미만 경고, 작업 전환 시 초기화, 병합 결과 순서 확인)
- [x] 병합 파일을 개별 삭제·비우기한 뒤 안내 문구의 파일 개수가 갱신되지 않는 문제 수정 (2026-09-25, 브라우저 시나리오 11단계 재확인)
- [x] 배포 후 브라우저가 이전 화면·스크립트를 계속 쓰지 않도록 첫 화면에 `Cache-Control: no-cache` 적용 (2026-09-25)
- [ ] OCR 결과 품질 및 전처리 회귀 테스트

## 작업 기록

### 구현 요약

- FastAPI 기본 앱, `GET /health`, 정적 웹 화면 구현
- 기능별 API 라우터 분리 및 앱 진입점 경량화
- 업로드 저장·검증, 보관 디렉터리 설정, 오래된 파일 정리 로직 구현
- 텍스트 추출 API와 결과 다운로드 API 구현, 결과 영역 `초기화` 버튼
- PDF 이미지·Word·Excel 변환, 병합, 분할, 압축 및 파일의 PDF 변환 구현
- PDF 병합 파일 누적 선택, 개별 삭제, 전체 비우기, 중복 방지 처리
- 텍스트 추출기, PDF 변환기, 유튜브 다운로드를 독립 메뉴로 구성
- `yt-dlp` 기반 유튜브 영상·MP3 다운로드, URL 제한 및 결과 파일 정리 구현
- 수동·자동 자막 VTT 추출과 중복 문구 정리 구현
- 다크 사이드바와 라임 포인트 중심의 반응형 UI로 개편
- OpenAI 프롬프트 번역과 Windows ComfyUI(Tailscale) 연동 이미지 생성 메뉴 구현

### 검증 기록

2026-09-04:

- `GET /health`: `{"status":"ok"}` 응답 확인
- 텍스트 파일 업로드, 추출 결과 및 다운로드 확인
- PDF의 이미지 ZIP 변환과 다운로드 확인
- TXT와 이미지 파일의 PDF 변환 확인
- PDF 2개 이상 병합과 PDF 분할 페이지 범위 검증
- PDF 압축, DOCX의 PDF 변환 및 잘못된 DOCX 예외 처리 검증
- 확장자와 실제 PDF 내용이 다른 업로드 거부 검증
- 유튜브 URL 정규화, 외부 도메인·재생목록 거부, 영상·MP3 설정 및 실패 정리 검증
- VTT 자막 정리, 자막 미제공 오류 및 자막 결과 다운로드 검증
- 화면 변경 후 정적 HTML/CSS와 기존 JavaScript 이벤트 연결 확인(브라우저 수동 확인)
- Docker Compose 빌드 및 실행 검증

2026-09-25:

- `pytest`: 52개 테스트 통과
- Tesseract 실행 파일 누락 오류, 만료 파일 정리 함수, 앱 시작 시 정리와 주기 정리 루프 검증
- PDF 변환 결과 생성, 텍스트 추출(OCR 포함), 주기 정리 루프의 워커 스레드 실행 검증
- PDF·DOCX 텍스트 추출, OCR 성공 경로(Tesseract 호출은 가짜 함수로 대체), `ffmpeg`·`ffprobe` 누락 오류 검증
- 병합 파일 브라우저 시나리오 11단계(Playwright/Chromium)와 첫 화면 `Cache-Control: no-cache` 응답 검증
- 운영: 비인증 요청 401, 가정용 회선 프록시를 거친 영상·MP3·자막 다운로드 확인

2026-09-25 (Phase 3 구현):

- `pytest`: 95개 테스트 통과
- ComfyUI 클라이언트: 템플릿 치환, 제출·폴링·다운로드 정상 흐름, 연결 실패, 스킴 없는 `COMFYUI_URL`, `node_errors`, 노드 미설치, 비 JSON 응답, 실행 오류, 시간 초과, 이미지 없는 결과, PNG 아닌 응답(모두 `httpx.MockTransport`)
- 번역기: 전체를 감싼 따옴표 한 쌍만 제거(문장 속 따옴표 유지), 공백 제거, 키 누락, 401·429·500, 연결 실패, 빈 결과, 형식 오류
- API: 빈·공백·2000자 초과 프롬프트의 한국어 422, 잘못된 크기, 오류별 502·503·504, PNG 저장·다운로드
- 화면: 외부 서비스 미설정 상태에서 메뉴 전환, 오류 안내, 390px 폭 표시 확인(Playwright/Chromium)

2026-09-25 (Phase 3 로컬 실제 검증, Mac mini → Tailscale → Windows ComfyUI 0.28.0):

- 생성: 세로 768×1024(첫 생성 약 80초, 모델 적재 포함), 가로 1024×768 23.5초, 정사각 1024×1024 25.0초, 요청마다 다른 seed, PNG 다운로드 확인
- 번역(`gpt-6-luna`): 3~4초, 자연스러운 영어 문장, 문장 속 따옴표(간판 글자) 유지 확인
- 브라우저: 번역 → 영어 수정 → 생성(23초) → 미리보기 → 다운로드 → 초기화 흐름, 처리 중 두 버튼 잠금 확인(Playwright/Chromium)
- 연결 불가(방화벽이 막은 포트): 연결 불가 안내가 28.6초 뒤 표시되어 연결 대기 한도를 5초로 줄임. Tailscale은 직접 연결이 아닌 DERP 중계로 연결됨

2026-09-25 (Phase 3 운영 검증):

- VPS 컨테이너 재빌드 후 컨테이너 안에서 `COMFYUI_URL/system_stats` 200 응답 확인
- `tools.manizu.blog`에서 한국어 번역 → 영어 확인 → 생성 → 미리보기 → 다운로드 정상 동작

### OCR 현황과 개선 메모

현재 이미지 OCR은 `app/services/text_extractor.py`에서 Tesseract를 직접 호출한다.

```python
pytesseract.image_to_string(image, lang="kor+eng")
```

정확도가 떨어질 수 있는 주요 원인은 다음과 같다.

- 이미지 확대, 흑백 변환, 대비 보정, 노이즈 제거, 이진화 등의 전처리가 없다.
- 한국어 문장에 `HBM4`, `LPX`, `AI`처럼 짧은 영문·숫자 토큰이 섞이면 인식 난도가 높다.
- 기본 OCR 모드를 사용해 문단, 줄바꿈, 공백 해석이 흔들릴 수 있다.
- OCR 후 공백과 줄바꿈을 정리하는 후처리 로직이 없다.

개선 우선순위:

1. 이미지 2배 확대
2. 그레이스케일 변환
3. 대비 보정 또는 이진화
4. `pytesseract`에 `--psm 6` 옵션 적용
5. OCR 결과의 공백과 줄바꿈 후처리
6. 필요 시 Google Vision, Azure OCR, Upstage OCR 같은 외부 OCR 검토

## 문서 검토 후속 조치 (2026-09-25)

2026-09-25 문서·구현 교차 검토에서 나온 문제 #1~#13의 처리 내역이다. 상세 근거는 로컬 전용 보고서 `docs/reviews/2026-09-25-doc-audit.md`에 있다(커밋 제외).

- [ ] #1 운영 환경에서 API 문서 화면(`/docs`, `/redoc`) 비활성화 여부 결정

처리 완료(2026-09-25):

- 운영: 개인 접근 제한(NPM Access List Basic Auth, 비인증 401 확인)(#1), NPM Proxy Host를 `DEPLOYMENT.md` 5절 설정과 일치(#5), NPM 관리 화면을 HTTPS 도메인으로만 접속
- 기능: yt-dlp JS 런타임을 Node 20에서 Deno 2.9.7로 교체(#3), 유튜브 가정용 회선 프록시(`YOUTUBE_PROXY`, `DEPLOYMENT.md` 11절) 구성과 운영 검증
- 문서: 운영 도메인 통일(#2), 진행 상태·배포 기록 갱신(#4, #7), 검증 기록 범위 정정(#6), PDF 변환 범위와 한계 기록(#8), `AGENTS.md` 갱신(#9), 표현 정리와 앱 이름 "Python AI Util" 통일(#10), 배포 문서 보강(#11), 로그 점검 기준 재작성(#12), 서버 스크린샷 Git 제외(#13)
- 테스트: 텍스트 추출·OCR 성공 경로, 워커 스레드 실행과 주기 정리 루프, `ffmpeg` 누락 오류
