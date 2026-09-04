# 기능 테스트 가이드

현재까지 구현된 Python AI 유틸리티 웹 기능을 로컬에서 확인하는 방법입니다.

## 1. Docker로 실행

프로젝트 루트에서 환경 변수 파일을 만들고 컨테이너를 실행합니다.

```bash
cp .env.example .env
docker compose up --build
```

실행 후 다음 주소로 접속합니다.

- 웹 화면: <http://localhost:8010>
- 상태 확인: <http://localhost:8010/health>

상태 확인 API가 아래 JSON을 반환하면 서버가 정상적으로 실행된 것입니다.

```json
{
  "status": "ok"
}
```

## 2. 테스트 가능한 기능

### 텍스트 추출기

- TXT 및 Markdown 텍스트 추출
- PDF 텍스트 추출
- DOCX 텍스트 추출
- PNG, JPG 등 이미지 OCR

OCR에는 Tesseract가 필요하므로 필요한 실행 파일이 포함된 Docker 환경에서 테스트하는 것을 권장합니다.

### PDF 변환기

- PDF를 이미지 ZIP으로 변환
- PDF를 Word 문서로 변환
- PDF를 Excel 문서로 변환
- PDF 병합
- PDF 페이지 범위 분할
- PDF 압축
- TXT, Markdown, DOCX 및 이미지 파일을 PDF로 변환

### 유튜브 도구

- 공개된 단일 유튜브 영상 다운로드
- MP3 음원 추출
- 한국어 또는 영어 자막 텍스트 추출

본인이 저장할 권한이 있는 콘텐츠에만 사용해야 합니다. 실제 다운로드 가능 여부는 영상 공개 범위, 지역·연령 제한 및 네트워크 상태에 따라 달라질 수 있습니다.

## 3. 자동 테스트 실행

로컬 가상환경을 활성화한 후 pytest를 실행합니다.

```bash
source .venv/bin/activate
pytest
```

현재 기준 자동 테스트는 총 35개입니다.

## 4. 결과 파일 보관

업로드 파일과 생성 결과는 각각 `uploads/`, `results/`에 저장됩니다. 기본 보관 기간은 24시간이며 앱 시작 시와 실행 중 60분 간격으로 만료 파일이 정리됩니다.

다음 환경 변수로 정책을 변경할 수 있습니다.

```dotenv
UPLOAD_RETENTION_HOURS=24
RESULT_RETENTION_HOURS=24
CLEANUP_INTERVAL_MINUTES=60
YOUTUBE_MAX_DOWNLOAD_MB=500
YOUTUBE_MAX_DURATION_SECONDS=7200
```

## 5. 종료

포그라운드에서 실행했다면 `Ctrl+C`로 중지합니다. 컨테이너와 네트워크까지 정리하려면 다음 명령을 사용합니다.

```bash
docker compose down
```
