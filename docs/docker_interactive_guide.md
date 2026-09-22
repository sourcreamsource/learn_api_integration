# 🟩 Docker 컨테이너 직접 접속 및 대화형 작업 절차서  

<br><br>

## 🟢 1. 직접 접속 방식이란 무엇인가?  

지금까지 사용했던 일회성 실행 방식(`docker run ... commit`)이 자판기 버튼을 누르고 음료수만 받고 끝나는 방식이었다면,  
**직접 접속 방식(Interactive Access)**은 **도커 컨테이너라는 독립된 작은 컴퓨터 방 안으로 내가 직접 걸어 들어가서 터미널을 열고 자유롭게 머무르며 작업하는 방식**이다.  

<br><br>

### 🟡 일회성 실행 vs 직접 접속 비교표  

| 비교 항목 | 일회성 실행 방식 (One-Shot) | 직접 접속 방식 (Interactive Shell) |
| :--- | :--- | :--- |
| 동작 형태 | 명령 1개 실행 후 컨테이너가 즉시 종료 및 삭제됨 | 컨테이너 셸 안에 상주하며 여러 명령어를 연속으로 실행 가능 |
| 터미널 화면 | 내 Mac 터미널에서 결과 글자만 출력되고 끝남 | 프롬프트가 `root@...:/workspace#`로 바뀌며 컨테이너 내부 환경이 됨 |
| 주 용도 | 자동화 스크립트, 단순 반복 실행 | 컨테이너 내부 환경 점검, 디버깅, 파일 구조 탐색, 수동 테스트 |
| 사용 명령어 | `docker run --rm ... commit` | `docker run -it --entrypoint bash ...` 또는 `docker exec` |

<br><br>

## 🟢 2. 사전 준비 (Prerequisites)  

컨테이너 안으로 들어가더라도 AI API를 호출하려면 비밀키가 필요하다.  
호스트 Mac 터미널에서 환경변수가 설정되어 있는지 먼저 확인한다.  

```bash
# Mac 터미널에서 환경변수 설정
export AI_API_KEY="본인의_실제_API_키"
export AI_API_FORMAT="openai"
export AI_MODEL="gpt-4o-mini"
```

- `export`: Export (내보내기) / 터미널에 환경변수를 등록하여 컨테이너로 전달할 준비  
- 실제 API Key를 코드나 파일에 적지 않고 호스트의 환경변수로만 안전하게 전달한다.  

<br><br>

## 🟢 3. 직접 접속하는 2가지 실무 방법  

<br><br>

### 🟡 방법 A: 접속용 일회성 컨테이너 실행 (가장 추천하는 간단한 방법)  

컨테이너를 켬과 동시에 내부의 `bash` 셸 화면으로 쏙 들어간다.  
작업을 마치고 나오면(`exit`) 컨테이너가 찌꺼기 없이 깔끔하게 자동 삭제된다.  

#### ⚫️ 1. 컨테이너 내부로 접속하기  
Mac 터미널에서 아래 명령을 실행한다.  

```bash
docker run --rm -it --entrypoint bash -v "$PWD:/workspace:ro" -e AI_API_KEY -e AI_API_FORMAT -e AI_MODEL ai-gitgen:local
```

##### ▫️ 명령어 및 옵션 풀네임 해설 표  

| 옵션 / 인자 | 풀네임 (Full Name) | 상세 역할 및 해설 |
| :--- | :--- | :--- |
| `docker` | Docker | 컨테이너 가상화 플랫폼 명령어 |
| `run` | Run (실행하다) | 이미지를 기반으로 새 컨테이너를 가동 |
| `--rm` | Remove (삭제하다) | 셸에서 나갈 때(`exit`) 사용했던 컨테이너를 자동 삭제하여 디스크 용량 절약 |
| `-i` | Interactive (대화형) | 내 키보드 입력(stdin)을 컨테이너 내부 셸로 계속 전달 |
| `-t` | Pseudo-TTY (가상 터미널) | 글자를 치고 볼 수 있는 터미널 화면(프롬프트) 창을 배정 |
| `--entrypoint bash` | Entry Point Replacement | Dockerfile에 고정된 기본 실행 파이썬 대신 `bash` 셸을 강제로 실행 |
| `-v "$PWD:/workspace:ro"` | Volume / Read-Only | 현재 내 Mac 폴더(`$PWD`)를 컨테이너 `/workspace`에 **읽기 전용(`:ro`)**으로 잠금 연결 |
| `-e AI_API_KEY` | Environment Variable | 내 Mac에 등록된 API Key를 컨테이너 환경변수로 안전하게 넘겨줌 |
| `ai-gitgen:local` | Image Name:Tag | 실행할 대상 로컬 이미지 이름 |

<br><br>

#### ⚫️ 2. 컨테이너 내부에서 직접 작업하기  
명령어를 치면 프롬프트가 `root@<컨테이너ID>:/workspace#` 모양으로 바뀐다.  
이제 당신은 Mac이 아니라 **격리된 Debian 리눅스 컨테이너 내부**에 들어온 상태다.  

여기서 다음 명령들을 차례대로 실행해본다.  

```bash
# 1) 현재 운영체제 확인 (Debian GNU/Linux 12인지 두 눈으로 확인)
cat /etc/os-release

# 2) 파이썬 버전 확인
python --version

# 3) 내 프로젝트 파일이 읽기 전용으로 잘 보이는지 확인
ls -la

# 4) Git 상태 확인
git status

# 5) AI 커밋 메시지 자동 생성 직접 실행!
python /app/main.py commit

# 6) AI PR 초안 자동 생성 직접 실행!
python /app/main.py pr
```

##### ▫️ 컨테이너 내부 명령어 풀네임 해설 표  

| 명령어 | 풀네임 (Full Name) | 상세 역할 |
| :--- | :--- | :--- |
| `cat` | Concatenate (이어붙이다/출력하다) | 텍스트 파일의 내용을 터미널 화면에 그대로 출력 |
| `ls -la` | List all / Long format | 숨김 파일을 포함한 모든 파일의 권한과 상세 목록 출력 |
| `git status` | Git Status (깃 상태) | 현재 Git 작업 트리의 변경 파일 현황 확인 |
| `python /app/main.py commit` | Python Interpreter Execution | 컨테이너 내부 `/app`에 설치된 AI GitGen 프로그램을 직접 구동 |

<br><br>

#### ⚫️ 3. 컨테이너 밖으로 빠져나오기  
작업이 모두 끝났으면 다음 명령어를 입력한다.  

```bash
exit
```

- `exit`: Exit (나가다/종료) / 컨테이너 셸을 닫고 내 원래 Mac 터미널로 복귀한다.  
- `--rm` 옵션을 주었기 때문에 방금 머물렀던 일회용 컨테이너는 자동으로 깨끗하게 지워진다.  

<br><br>

### 🟡 방법 B: 컨테이너를 백그라운드에 켜두고 수시로 드나들기 (고급 개발자 방식)  

컨테이너를 백그라운드(뒤편)에서 계속 켜두고, 필요할 때마다 `exec` 명령어로 들어갔다 나왔다 하는 방식이다.  

#### ⚫️ 1. 백그라운드 상주 컨테이너 켜기  

```bash
docker run -d --name gitgen-dev -v "$PWD:/workspace:ro" -e AI_API_KEY -e AI_API_FORMAT -e AI_MODEL --entrypoint sleep ai-gitgen:local infinity
```

##### ▫️ 옵션 해설 표  

| 옵션 | 풀네임 (Full Name) | 상세 역할 |
| :--- | :--- | :--- |
| `-d` | Detached Mode (분리 실행) | 터미널을 차지하지 않고 백그라운드 데몬으로 계속 실행 |
| `--name gitgen-dev` | Container Name (컨테이너 이름) | 컨테이너에 알아보기 쉬운 별명(`gitgen-dev`)을 붙임 |
| `--entrypoint sleep` | Entry Point | 컨테이너가 바로 꺼지지 않도록 잠자기 명령을 진입점으로 지정 |
| `infinity` | Infinity (무한히) | 무한히 대기하여 컨테이너가 살아있도록 유지 |

<br><br>

#### ⚫️ 2. 실행 중인 컨테이너 안으로 들어가기 (`exec`)  

```bash
docker exec -it gitgen-dev bash
```

- `exec`: Execute (실행하다) / 이미 켜져 있는 컨테이너 안으로 새 명령 프로세스를 밀어 넣음  
- 들어가서 마음껏 `python /app/main.py commit` 등의 작업을 수행한다.  
- 작업을 마치고 `exit`를 입력해도 컨테이너는 꺼지지 않고 계속 백그라운드에서 살아있다.  

<br><br>

#### ⚫️ 3. 상주 컨테이너 완전히 종료 및 삭제하기  
모든 실습이 끝나서 컨테이너를 끌 때는 다음 2개 명령을 실행한다.  

```bash
# 1) 켜져 있는 컨테이너 멈추기
docker stop gitgen-dev

# 2) 멈춘 컨테이너 삭제하기
docker rm gitgen-dev
```

- `stop`: Stop (정지) / 실행 중인 컨테이너 프로세스를 안전하게 종료  
- `rm`: Remove (삭제) / 디스크에 남아있는 컨테이너 기록을 완전히 삭제  

<br><br>

## 🟢 4. Docker Compose로 대화형 Bash 접속하기  

복잡한 `docker run` 명령 대신 `compose.yaml`을 사용할 경우 아래 한 줄로 즉시 접속할 수 있다.  

```bash
docker compose run --rm --entrypoint bash ai-gitgen
```

- `compose run`: `compose.yaml`에 적힌 볼륨과 환경변수 설정을 그대로 가져와서 1회성 컨테이너 실행  
- `--rm`: 접속 종료(`exit`) 시 컨테이너 자동 파기  
- `--entrypoint bash`: 진입점을 bash 셸로 변경  

<br><br>

## 🟢 5. 직접 접속 시 주의해야 할 보안 수칙  

| 주의 사항 | 위험 요인 | 올바른 예방 조치 |
| :--- | :--- | :--- |
| **호스트 파일 수정 시도** | 컨테이너 내부에서 소스 코드를 실수로 삭제/변조 | 볼륨 마운트 시 반드시 `:ro`(Read-Only)가 적용되어 있으므로 컨테이너 내부에서는 파일 수정이 원천 거부됨 (`Read-only file system` 안내 출력) |
| **API Key 화면 노출** | `env` 명령어로 컨테이너의 모든 환경변수 출력 시 키 노출 위험 | 타인과 화면을 공유하거나 터미널 캡처 시 `env`나 `printenv` 명령어를 함부로 화면에 띄우지 말 것 |
| **컨테이너 잔존 누적** | `--rm` 없이 접속했다가 나가면 멈춘 컨테이너가 디스크를 계속 차지 | 반드시 `--rm` 플래그를 사용하거나, 실습 종료 후 `docker ps -a`로 미사용 컨테이너를 확인하고 정리 |
