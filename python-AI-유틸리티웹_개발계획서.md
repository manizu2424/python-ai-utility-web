# Python 유틸리티 웹 개발계획서 (개인 활용 목적)

## 1. 개요

| 항목 | 내용 |
|---|---|
| 프로젝트명 | (가칭) 유틸리티 툴박스 |
| 목적 | 개인이 자주 쓰는 텍스트 추출, 파일 변환, 미디어 다운로드 기능을 웹 UI로 편리하게 사용 |
| 사용자 범위 | 본인 전용 (비공개, 로그인/과금 없음) |
| 실행 환경 | Contabo VPS (4 vCPU / 8GB RAM / 150GB SSD) + Docker |
| 기존 자산 활용 | 도메인(manizu.kr 서브도메인) |

카페24 공유호스팅은 Python 상시 실행이 불가능해 배제하고, 이미 확보된 Contabo VPS에 Docker 기반으로 구축.

---

## 2. 기능 구성

### 2.1 기본 유틸리티
- **텍스트 추출기**: 이미지/PDF/문서 → 텍스트 (OCR 포함)
- **PDF 변환기**: PDF ↔ Word/Excel/이미지, 병합/분할/압축
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
| 파일 처리 | PyMuPDF, python-docx, openpyxl, yt-dlp, ffmpeg, Tesseract OCR |
| 인프라 | Docker Compose, Nginx Proxy Manager, Contabo VPS |

---

## 4. 시스템 아키텍처

```
[본인 브라우저]
      │ 파일 업로드
      ▼
[Nginx Proxy Manager] ── tools.manizu.kr 라우팅
      │
      ▼
[FastAPI 컨테이너] ── 변환/추출 처리
      │
      └─ 결과 파일 또는 추출 텍스트 반환
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
- **접근 제한**: 외부 공개 서비스가 아니므로 IP 화이트리스트 또는 간단한 Basic Auth 정도로 접근 제한 (본인 외 접근 방지)
- **HTTPS**: Nginx Proxy Manager로 Let's Encrypt 인증서 적용

---

## 7. 다음 액션

1. Contabo VPS에 Docker/Docker Compose 설치 확인
2. Nginx Proxy Manager 컨테이너 기동 + 서브도메인(tools.manizu.kr) 연결
3. FastAPI 기본 프로젝트 골격 생성 (텍스트 추출기부터)
4. 운영 배포 전 개인 접근 제한과 HTTPS 설정
