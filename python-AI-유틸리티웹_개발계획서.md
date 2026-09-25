# Python AI Util 개발계획서 (개인 활용 목적)

## 1. 개요

| 항목 | 내용 |
|---|---|
| 프로젝트명 | Python AI Util |
| 목적 | 개인이 자주 쓰는 텍스트 추출, 파일 변환, 미디어 다운로드 기능을 웹 UI로 편리하게 사용 |
| 사용자 범위 | 본인 전용 (비공개, 로그인/과금 없음) |
| 실행 환경 | Contabo VPS (4 vCPU / 8GB RAM / 150GB SSD) + Docker |
| 기존 자산 활용 | 도메인(manizu.blog 서브도메인, `tools.manizu.blog`) |

카페24 공유호스팅은 Python 상시 실행이 불가능해 배제하고, 이미 확보된 Contabo VPS에 Docker 기반으로 구축.

---

## 2. 기능 구성

### 2.1 기본 유틸리티
- **텍스트 추출기**: 이미지/PDF/문서 → 텍스트 (OCR 포함)
- **PDF 변환기**: PDF → 이미지/Word/Excel(텍스트 기반, 레이아웃·표 미보존), 텍스트·Word·이미지 → PDF, 병합/분할/압축
- **유튜브 다운로드**: 영상/음원 추출 (개인 소장용)

### 2.2 유튜브 자막 도구
- 한국어 또는 영어 자막 텍스트 추출
- 추출 결과 화면 표시 및 텍스트 파일 다운로드

---

## 3. 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python (FastAPI) |
| 프론트엔드 | 단순 HTML/JS (개인용이므로 화려한 UI 불필요, 기능 우선) |
| 파일 처리 | PyMuPDF, python-docx, openpyxl, reportlab, Pillow, yt-dlp(+ Deno JS 런타임), ffmpeg, Tesseract OCR |
| 인프라 | Docker Compose, Nginx Proxy Manager, Contabo VPS, Tailscale(유튜브 가정용 회선 경유) |

---

## 4. 시스템 아키텍처

```
[본인 브라우저]
      │ 파일 업로드
      ▼
[Nginx Proxy Manager] ── tools.manizu.blog 라우팅
      │
      ▼
[FastAPI 컨테이너] ── 변환/추출 처리
      │
      ├─ 결과 파일 또는 추출 텍스트 반환
      │
      └─ 유튜브 요청만 ── Tailscale ──▶ [집 Mac mini SOCKS5 프록시] ──▶ YouTube
```

---

## 5. 개발 단계 (개인 진행 일정 예시)

| 단계 | 기간(안) | 내용 |
|---|---|---|
| Phase 0 | 1주 | Docker/Nginx Proxy Manager 세팅, 서브도메인 연결 |
| Phase 1 | 2~3주 | 텍스트 추출기, PDF 변환기 구현 |
| Phase 2 | 2주 | 유튜브 영상·음원 다운로드와 자막 텍스트 추출 |

과금/사용자 관리가 없으므로 기능 단위로 필요할 때마다 이어서 개발하면 됨.

---

## 6. 운영 시 참고사항 (개인용 기준)

- **파일 자동 삭제**: 업로드/결과 파일은 처리 후 일정 시간 뒤 자동 삭제 (디스크 관리 목적)
- **접근 제한**: 외부 공개 서비스가 아니므로 Nginx Proxy Manager Access List의 Basic Auth로 본인 외 접근을 막음 (`DEPLOYMENT.md` 5절)
- **HTTPS**: Nginx Proxy Manager로 Let's Encrypt 인증서 적용
- **유튜브 접근**: 데이터센터 IP는 유튜브가 차단하므로 가정용 회선(Mac mini)의 SOCKS5 프록시를 Tailscale로 경유 (`DEPLOYMENT.md` 11절)

---

## 7. 진행 현황

- 2026-09-04: Phase 0~2 구현 완료, VPS 배포(Nginx Proxy Manager, Let's Encrypt HTTPS)
- 2026-09-25: 개인 접근 제한(Basic Auth) 적용, 유튜브 JS 런타임(Deno)과 가정용 회선 프록시 지원 추가, 앱 이름 통일, 테스트 보강, PDF 병합 화면 오류 수정

남은 작업은 `TASKS.md`에서 관리한다.
