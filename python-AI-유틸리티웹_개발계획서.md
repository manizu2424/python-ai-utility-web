# Python + AI 유틸리티 웹 개발계획서 (개인 활용 목적)

## 1. 개요

| 항목 | 내용 |
|---|---|
| 프로젝트명 | (가칭) AI 유틸리티 툴박스 |
| 목적 | 개인이 자주 쓰는 텍스트 추출, 파일 변환, 미디어 다운로드 기능을 웹 UI로 만들어 편하게 사용 + AI로 보조 |
| 사용자 범위 | 본인 전용 (비공개, 로그인/과금 없음) |
| 실행 환경 | Contabo VPS (4 vCPU / 8GB RAM / 150GB SSD) + Docker |
| 기존 자산 활용 | n8n(n8n2.manizu.kr), 도메인(manizu.kr 서브도메인) |

카페24 공유호스팅은 Python 상시 실행이 불가능해 배제하고, 이미 확보된 Contabo VPS에 Docker 기반으로 구축.

---

## 2. 기능 구성

### 2.1 기본 유틸리티
- **텍스트 추출기**: 이미지/PDF/문서 → 텍스트 (OCR 포함)
- **PDF 변환기**: PDF ↔ Word/Excel/이미지, 병합/분할/압축
- **유튜브 다운로드**: 영상/음원 추출 (개인 소장용)

### 2.2 AI 보조 기능
- 추출된 텍스트 **요약 / 번역 / 맞춤법 교정**
- 유튜브 자막 추출 → **AI 요약** (긴 영상 핵심만 빠르게 보기)
- PDF 문서 **AI 기반 Q&A** (업로드한 문서에 질문하면 답변)
- 이미지 → AI 설명/태깅

개인 도구이므로 필요한 기능만 하나씩 붙여가며 확장하는 방식으로 진행.

---

## 3. 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python (FastAPI) |
| 프론트엔드 | 단순 HTML/JS (개인용이므로 화려한 UI 불필요, 기능 우선) |
| AI 연동 | OpenAI / Claude / Gemini API |
| 파일 처리 | PyMuPDF, python-docx, openpyxl, yt-dlp, ffmpeg, Tesseract OCR |
| 오케스트레이션 | n8n (AI 처리 파이프라인, 결과 알림) |
| 인프라 | Docker Compose, Nginx Proxy Manager, Contabo VPS |

### n8n 활용 관점
- FastAPI가 **무거운 처리(OCR, 변환, ffmpeg)** 담당
- n8n은 **AI 호출 및 후처리**를 담당해, 기능 추가/수정 시 코드 재배포 없이 워크플로우만 조정하면 되는 구조로 설계

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
      ├─ (단순 변환) → 결과 파일 즉시 반환
      │
      └─ (AI 기능) → n8n Webhook 호출 → LLM API → 결과 반환
```

---

## 5. 개발 단계 (개인 진행 일정 예시)

| 단계 | 기간(안) | 내용 |
|---|---|---|
| Phase 0 | 1주 | Docker/Nginx Proxy Manager 세팅, 서브도메인 연결 |
| Phase 1 | 2~3주 | 텍스트 추출기, PDF 변환기 구현 (AI 없이 순수 변환) |
| Phase 2 | 2주 | 유튜브 다운로드 추가 + AI 요약 기능 1개 연동 |
| Phase 3 | 2주 | 번역/Q&A 등 AI 기능 확장 |

과금/사용자 관리가 없으므로 기능 단위로 필요할 때마다 이어서 개발하면 됨.

---

## 6. 운영 시 참고사항 (개인용 기준)

- **파일 자동 삭제**: 업로드/결과 파일은 처리 후 일정 시간 뒤 자동 삭제 (디스크 관리 목적)
- **API 비용**: 개인 사용량 기준이라 크지 않지만, LLM 호출량은 간단히 로그로 확인해두면 좋음
- **접근 제한**: 외부 공개 서비스가 아니므로 IP 화이트리스트 또는 간단한 Basic Auth 정도로 접근 제한 (본인 외 접근 방지)
- **HTTPS**: Nginx Proxy Manager로 Let's Encrypt 인증서 적용

---

## 7. 다음 액션

1. Contabo VPS에 Docker/Docker Compose 설치 확인
2. Nginx Proxy Manager 컨테이너 기동 + 서브도메인(tools.manizu.kr) 연결
3. FastAPI 기본 프로젝트 골격 생성 (텍스트 추출기부터)
4. 필요 시 n8n에 AI 요약 워크플로우 프로토타입 제작
