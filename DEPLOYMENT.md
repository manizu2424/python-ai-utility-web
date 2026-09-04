# VPS 배포 및 운영 가이드

이 문서는 Ubuntu 기반 Contabo VPS에 앱을 배포하고 Nginx Proxy Manager(NPM)를
통해 `tools.manizu.kr`로 서비스하는 절차입니다. 앱 포트는 기본적으로
`127.0.0.1:8010`에만 바인딩하고, 외부 요청은 NPM 공유 Docker 네트워크를 통해
컨테이너의 `8000` 포트로 전달합니다.

## 1. 사전 준비

- `tools.manizu.kr`의 DNS A 레코드를 VPS 공인 IPv4 주소로 설정합니다.
- VPS 방화벽에서는 SSH, HTTP, HTTPS에 필요한 `22`, `80`, `443` 포트만 허용합니다.
- Nginx Proxy Manager를 먼저 실행하고 관리 화면에 접속할 수 있어야 합니다.
- 운영 계정은 SSH 키로 로그인하고, 비밀번호 로그인과 root 직접 로그인은 가능한 한 비활성화합니다.

Docker가 공개한 포트는 UFW 규칙을 우회할 수 있으므로 앱 포트 `8010`을
`0.0.0.0`에 공개하지 않습니다.

## 2. Docker 설치

이미 Docker Engine과 Compose 플러그인이 설치되어 있다면 버전만 확인합니다.

```bash
docker --version
docker compose version
```

설치되어 있지 않다면 [Docker Engine Ubuntu 공식 설치 문서](https://docs.docker.com/engine/install/ubuntu/)에
따라 Docker 공식 apt 저장소를 등록한 후 다음 패키지를 설치합니다.

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

그룹 변경은 로그아웃 후 다시 로그인해야 적용됩니다. 설치 확인은 다음과 같이 합니다.

```bash
docker run --rm hello-world
docker compose version
```

## 3. 프로젝트 배치

GitHub 저장소를 `/opt/python-ai-utility-web`에 복제합니다.

```bash
sudo mkdir -p /opt/python-ai-utility-web
sudo chown "$USER":"$USER" /opt/python-ai-utility-web
git clone https://github.com/manizu2424/python-ai-utility-web.git /opt/python-ai-utility-web
cd /opt/python-ai-utility-web
cp .env.example .env
chmod 600 .env
```

`.env`의 운영값을 확인합니다. 아래 항목은 운영 권장값입니다.

```dotenv
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
BIND_ADDRESS=127.0.0.1
HOST_PORT=8010
UPLOAD_DIR=/tmp/ai-toolbox/uploads
RESULT_DIR=/tmp/ai-toolbox/results
MAX_UPLOAD_MB=100
UPLOAD_RETENTION_HOURS=24
RESULT_RETENTION_HOURS=24
CLEANUP_INTERVAL_MINUTES=60
YOUTUBE_MAX_DOWNLOAD_MB=500
YOUTUBE_MAX_DURATION_SECONDS=7200
NPM_NETWORK=nginx-proxy-manager_default
CONTAINER_CPU_LIMIT=2.0
CONTAINER_MEMORY_LIMIT=2g
```

`NPM_NETWORK`에는 실제 Nginx Proxy Manager 컨테이너가 연결된 Docker 네트워크
이름을 사용해야 합니다. 현재 서버에서 확인한 값은
`nginx-proxy-manager_default`입니다. 다음 명령으로 다시 확인할 수 있습니다.

```bash
docker network ls --format '{{.Name}}'
docker inspect <NPM_컨테이너명> --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}'
```

`CONTAINER_CPU_LIMIT`와 `CONTAINER_MEMORY_LIMIT`는 여러 서비스가 함께 실행되는
VPS에서 이 앱이 사용할 수 있는 최대 자원을 제한합니다. 서버 사양에 따라 조정하세요.

`uploads/`와 `results/`는 자동 생성되며, 결과 파일은 기본 24시간 뒤 삭제됩니다.

## 4. 최초 실행

운영 오버라이드를 포함해 이미지를 빌드하고 컨테이너를 시작합니다.

```bash
cd /opt/python-ai-utility-web
docker compose -f docker-compose.yml -f compose.production.yml config --quiet
docker compose -f docker-compose.yml -f compose.production.yml up -d --build
docker compose -f docker-compose.yml -f compose.production.yml ps
curl -fsS http://127.0.0.1:8010/health
```

상태 확인 결과가 `{"status":"ok"}`이고 `ps`의 상태가 `healthy`이면 앱이
정상적으로 실행된 것입니다.

Portainer에서 실행 상태를 볼 수 있지만, 이 프로젝트는 기본 Compose와 운영
오버라이드를 함께 병합하므로 최초 배포와 업데이트는 위 CLI 명령 사용을 권장합니다.

## 5. Nginx Proxy Manager 연결

NPM 관리 화면에서 `Proxy Hosts` → `Add Proxy Host`를 선택하고 다음과 같이 설정합니다.

- Domain Names: `tools.manizu.kr`
- Scheme: `http`
- Forward Hostname / IP: `ai-toolbox`
- Forward Port: `8000`
- Block Common Exploits: 활성화
- Websockets Support: 활성화

Advanced 설정에는 업로드 크기와 긴 변환 요청을 고려해 다음 값을 추가합니다.

```nginx
client_max_body_size 110m;
proxy_connect_timeout 60s;
proxy_read_timeout 7200s;
proxy_send_timeout 7200s;
```

SSL 탭에서 새 Let's Encrypt 인증서를 발급한 뒤 `Force SSL`을 활성화합니다.
HTTPS 접속이 정상임을 먼저 확인한 후 HSTS를 활성화합니다.

개인용 서비스이므로 NPM의 `Access Lists`에서 Basic Auth 계정을 만들거나 접근
가능한 IP 대역을 제한하고, 해당 Access List를 Proxy Host에 연결합니다.

운영 공개 전에는 Access List 연결, SSL `Force SSL`, 업로드 제한 설정을 모두
확인해야 합니다.

## 6. 배포 후 점검

```bash
curl -fsS https://tools.manizu.kr/health
docker compose -f docker-compose.yml -f compose.production.yml ps
docker compose -f docker-compose.yml -f compose.production.yml logs --tail=100 ai-toolbox
```

브라우저에서는 다음 기능을 각각 한 번씩 확인합니다.

1. TXT 파일 텍스트 추출 및 결과 다운로드
2. PDF 변환 또는 병합
3. 권한이 있는 공개 유튜브 영상의 자막 텍스트 추출

상세 기능 점검은 `TESTING_GUIDE.md`를 따릅니다.

## 7. 업데이트 배포

배포 전 현재 커밋을 기록하면 문제 발생 시 되돌리기 쉽습니다.

```bash
cd /opt/python-ai-utility-web
git rev-parse --short HEAD
git pull --ff-only origin main
docker compose -f docker-compose.yml -f compose.production.yml up -d --build
docker compose -f docker-compose.yml -f compose.production.yml ps
curl -fsS http://127.0.0.1:8010/health
```

## 8. 재시작 및 장애 확인

```bash
cd /opt/python-ai-utility-web
docker compose -f docker-compose.yml -f compose.production.yml restart ai-toolbox
docker compose -f docker-compose.yml -f compose.production.yml logs --tail=200 ai-toolbox
docker compose -f docker-compose.yml -f compose.production.yml ps
```

이미지 재빌드가 필요하면 `restart` 대신 다음 명령을 사용합니다.

```bash
docker compose -f docker-compose.yml -f compose.production.yml up -d --build
```

컨테이너 로그는 Docker `json-file` 드라이버로 파일당 10MB, 최대 3개까지
순환 보관합니다. 앱은 `restart: unless-stopped`로 설정되어 VPS 재부팅이나
비정상 종료 후 자동 재시작됩니다.

## 9. 롤백

업데이트 전 기록한 정상 커밋으로 전환한 뒤 이미지를 다시 빌드합니다.

```bash
cd /opt/python-ai-utility-web
git fetch origin
git switch --detach <정상_커밋_해시>
docker compose -f docker-compose.yml -f compose.production.yml up -d --build
curl -fsS http://127.0.0.1:8010/health
```

문제가 해결되면 `git switch main`으로 복귀하고 필요한 수정 사항을 반영합니다.

## 10. 백업과 보안

- Git으로 관리되는 앱 코드는 GitHub 원격 저장소를 기준으로 복구합니다.
- 서버의 `.env`와 NPM 설정·인증서 데이터는 암호화된 별도 저장소에 백업합니다.
- `uploads/`와 `results/`는 임시 데이터이므로 기본적으로 백업하지 않습니다.
- `.env`, 업로드 원본, 생성 결과 파일은 Git에 커밋하지 않습니다.
- OS와 Docker 패키지에 보안 업데이트를 적용하고, 배포 후 상태 확인을 수행합니다.
- 접근 로그나 오류 보고를 공유할 때 영상 URL, 파일명 등 개인 정보를 제거합니다.
