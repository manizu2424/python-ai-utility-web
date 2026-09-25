# VPS 배포 및 운영 가이드

이 문서는 Ubuntu 기반 Contabo VPS에 앱을 배포하고 Nginx Proxy Manager(NPM)를
통해 `tools.manizu.blog`로 서비스하는 절차입니다. 앱 포트는 기본적으로
`127.0.0.1:8010`에만 바인딩하고, 외부 요청은 NPM 공유 Docker 네트워크를 통해
컨테이너의 `8000` 포트로 전달합니다.

## 1. 사전 준비

- `tools.manizu.blog`의 DNS A 레코드를 VPS 공인 IPv4 주소로 설정합니다.
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

현재 서버의 Docker 프로젝트 공통 경로인 `/home/docker` 아래에 GitHub 저장소를
복제합니다. Nginx Proxy Manager도 `/home/docker/nginx-proxy-manager`에서
운영되고 있습니다.

```bash
cd /home/docker
git clone https://github.com/manizu2424/python-ai-utility-web.git pytool
cd /home/docker/pytool
cp .env.example .env
chmod 600 .env
```

저장소를 비공개로 전환한 경우 GitHub는 HTTPS 비밀번호 인증을 지원하지 않으므로
clone과 `git pull`에 개인 액세스 토큰(PAT)이나 읽기 전용 deploy key(SSH)를 사용합니다.

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
cd /home/docker/pytool
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

- Domain Names: `tools.manizu.blog`
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

`client_max_body_size`는 요청 전체 크기 제한입니다. 앱의 `MAX_UPLOAD_MB`는 파일당
제한이므로 PDF 병합처럼 여러 파일을 한 번에 보내는 요청은 합계가 110MB를 넘으면
NPM에서 413으로 거부됩니다. 큰 파일을 자주 병합한다면 이 값을 함께 늘립니다.

SSL 탭에서 새 Let's Encrypt 인증서를 발급한 뒤 `Force SSL`을 활성화합니다.
HTTPS 접속이 정상임을 먼저 확인한 후 HSTS를 활성화합니다.

개인용 서비스이므로 NPM의 `Access Lists`에서 Basic Auth 접근 제한을 만들고
Proxy Host의 Details 탭에서 연결합니다.

- Details: `Satisfy Any` 끔, `Pass Auth to Host` 끔
- Authorization: 사용자 이름과 다른 곳에서 쓰지 않는 긴 비밀번호
- Access: `allow` / `all` 규칙 하나. NPM이 규칙 뒤에 `deny all`을 자동으로 붙이므로
  허용 규칙이 필요합니다. `allow all` 상태에서 `Satisfy Any`를 켜면 비밀번호 없이
  접속되므로 반드시 끕니다.

연결 후 인증 없이 `curl -s -o /dev/null -w '%{http_code}' https://<도메인>/`을 실행해
`401`이 나오는지 확인합니다.

운영 공개 전에는 Access List 연결, SSL `Force SSL`, 업로드 제한 설정을 모두
확인해야 합니다.

## 6. 배포 후 점검

```bash
# Access List 적용 상태: 인증 없이 401, 인증 시 {"status":"ok"}
curl -s -o /dev/null -w '%{http_code}\n' https://tools.manizu.blog/health
curl -fsS -u '<사용자>:<비밀번호>' https://tools.manizu.blog/health
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
cd /home/docker/pytool
git rev-parse --short HEAD
git pull --ff-only origin main
docker compose -f docker-compose.yml -f compose.production.yml up -d --build
docker compose -f docker-compose.yml -f compose.production.yml ps
curl -fsS http://127.0.0.1:8010/health
```

## 8. 재시작 및 장애 확인

```bash
cd /home/docker/pytool
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
cd /home/docker/pytool
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

## 11. 유튜브 가정용 회선 경유

Contabo 같은 데이터센터 IP에서는 유튜브가 요청을 봇으로 보고 차단합니다. 그래서
유튜브 요청만 집의 Mac mini(가정용 회선)를 거치도록 SOCKS5 프록시를 둡니다.
프록시는 Tailscale 사설망에만 열어 인터넷과 집 LAN에는 노출하지 않습니다.
나머지 기능은 영향을 받지 않습니다. 다운로드한 파일은 집 회선의 업로드 대역폭을
사용하고, Mac mini가 꺼져 있거나 잠자기 상태이면 유튜브 기능이 실패합니다.

### 11.1 Tailscale 연결

Mac mini와 VPS를 같은 Tailscale 계정(tailnet)에 로그인합니다.

```bash
# VPS
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Mac mini: Tailscale 앱으로 로그인한 뒤 IP 확인
tailscale ip -4
```

이하 Mac mini의 Tailscale IP를 `100.x.y.z`로 표기합니다.

### 11.2 Mac mini에 SOCKS5 프록시 실행

`microsocks`를 설치하고 Tailscale IP에만 바인딩합니다. 사용자 이름과 비밀번호를
지정해 tailnet의 다른 기기가 프록시를 쓰지 못하게 합니다.

```bash
brew install microsocks
microsocks -i 100.x.y.z -p 1080 -u <사용자> -P <비밀번호>
```

재부팅 후에도 자동으로 실행되도록 `~/Library/LaunchAgents/local.youtube-proxy.plist`를
만듭니다. LaunchAgent는 로그인한 사용자 세션에서 실행되므로 Mac mini의 자동
로그인을 켜 둡니다.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>local.youtube-proxy</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/microsocks</string>
    <string>-i</string><string>100.x.y.z</string>
    <string>-p</string><string>1080</string>
    <string>-u</string><string>사용자</string>
    <string>-P</string><string>비밀번호</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
```

```bash
chmod 600 ~/Library/LaunchAgents/local.youtube-proxy.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.youtube-proxy.plist
launchctl print gui/$(id -u)/local.youtube-proxy | grep state
```

Tailscale보다 먼저 시작되어 바인딩에 실패하더라도 `KeepAlive`가 다시 실행합니다.
시스템 설정의 에너지 항목에서 자동 잠자기를 끄거나 `sudo pmset -a sleep 0`을
적용합니다.

### 11.3 VPS 앱 설정

서버 `.env`에 프록시 주소를 추가하고 컨테이너를 다시 만듭니다.

```dotenv
YOUTUBE_PROXY=socks5://<사용자>:<비밀번호>@100.x.y.z:1080
```

```bash
cd /home/docker/pytool
docker compose -f docker-compose.yml -f compose.production.yml up -d
docker exec ai-toolbox python -c "import socket; socket.create_connection(('100.x.y.z', 1080), 5); print('proxy reachable')"
```

컨테이너에서 프록시에 연결되지 않으면 VPS에서 `tailscale status`로 Mac mini가
보이는지 먼저 확인합니다. 연결되면 웹 화면에서 짧은 공개 영상으로 영상·MP3·자막을
각각 확인합니다. `YOUTUBE_PROXY`를 비우면 다시 직접 연결합니다.

### 11.4 Mac mini 영향과 프록시 관리

프록시는 Tailscale 주소의 `1080` 포트로 들어오는 연결만 처리합니다. macOS 시스템
프록시, DNS, 라우팅, Tailscale 설정은 바꾸지 않으므로 Mac mini의 개발 작업과
원격 접속(SSH, 화면 공유, VS Code Remote 등)에는 영향이 없습니다. 대기 중 자원
사용은 CPU 0%, 메모리 약 5MB입니다.

다만 다음 사항은 알아 둡니다.

- 운영 사이트에서 유튜브를 받는 동안 데이터가 "유튜브 → Mac mini → VPS"로 흐르므로
  집 회선의 업로드 대역폭을 사용합니다. 큰 영상을 받는 동안 원격 접속이 느려질 수 있습니다.
- 유튜브 요청이 집 IP에서 나가므로 짧은 시간에 많이 받으면 집에서도 유튜브 봇 확인이
  나타날 수 있습니다.
- 다른 프로그램이 `0.0.0.0:1080`을 사용하려 하면 충돌하므로 프록시 포트를 바꿉니다.
- 재시작 후 로그인하기 전까지는 LaunchAgent가 실행되지 않아 유튜브 기능이 실패합니다.

프록시 관리 명령은 다음과 같습니다. 프록시를 꺼도 운영 사이트의 유튜브 기능만
실패하고 나머지 기능은 영향을 받지 않습니다.

```bash
# 지금만 중지 (다음 로그인 때 다시 실행됨)
launchctl bootout gui/$(id -u)/local.youtube-proxy

# 계속 꺼 두기 (재부팅·재로그인 후에도 실행 안 됨)
launchctl disable gui/$(id -u)/local.youtube-proxy
launchctl bootout gui/$(id -u)/local.youtube-proxy

# 다시 켜기
launchctl enable gui/$(id -u)/local.youtube-proxy
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.youtube-proxy.plist

# 상태 확인
launchctl print gui/$(id -u)/local.youtube-proxy | grep -E "^\s*state"

# 완전히 제거 (중지한 뒤)
rm ~/Library/LaunchAgents/local.youtube-proxy.plist
brew uninstall microsocks
```

완전히 제거한 뒤에는 VPS `.env`의 `YOUTUBE_PROXY` 값을 비우고 컨테이너를 다시
만들어 직접 연결로 되돌립니다. 이 경우 VPS에서는 유튜브 기능이 동작하지 않습니다.
