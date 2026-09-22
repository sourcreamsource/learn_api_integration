# 🟩 AI GitGen Docker 명령어 기반 사용 가이드  

<br><br>

## 🟢 1. Docker 도입 목적과 설계 의도  

AI GitGen 프로젝트에서 Docker(도커)를 사용하는 핵심 의도는 로컬 컴퓨터의 복잡한 파이썬 환경 설정이나 버전 충돌 없이, **누구나 독립되고 격리된 리눅스 환경에서 안전하게 커밋 메시지와 PR 초안을 생성**할 수 있도록 지원하는 것이다.  

<br><br>

### 🟡 핵심 보안 및 설계 3대 원칙  

| 설계 원칙 | 상세 내용 | 도입 이유 |
| :--- | :--- | :--- |
| **API Key 이미지 분리** | Docker 이미지 파일 내부에 `AI_API_KEY`를 절대 복사(`COPY`)하거나 하드코딩하지 않음 | 이미지가 외부에 공유되거나 유출되어도 보안 비밀키가 안전하게 보호됨 |
| **호스트 저장소 읽기 전용 (`:ro`)** | 내 컴퓨터의 소스 코드 폴더를 컨테이너에 마운트할 때 반드시 Read-Only(`:ro`) 잠금을 적용 | 컨테이너 내부 프로그램이 호스트의 소스 코드를 실수로 변조하거나 삭제하는 위험을 원천 차단 |
| **경량화 및 보안 필터링** | `.dockerignore`를 통해 `.git`, `.env`, `_temporary` 폴더를 빌드 문맥에서 완전히 배제 | 불필요한 빌드 용량 낭비를 막고 민감한 설정 정보의 유입을 물리적으로 차단 |

<br><br>

### 🟡 컨테이너 OS 환경에 대한 팩트  
- 본 프로젝트의 컨테이너 환경은 **우분투(Ubuntu)가 아닌 데비안(Debian 12 Bookworm)** 기반의 공식 파이썬 슬림 이미지(`python:3.12-slim`)로 제작되었다.  
- 불필요한 시스템 패키지를 덜어내어 150MB 수준의 아주 가벼운 용량과 빠른 다운로드 및 빌드 속도를 보장한다.  

<br><br>

## 🟢 2. 사전 준비 (Prerequisites)  

컨테이너를 실행하기 전 호스트 Mac 터미널에서 다음 2가지 준비를 완료해야 한다.  

<br><br>

### 🟡 1) Docker 데몬(Docker Desktop) 실행 확인  
Mac 화면 상단 메뉴 바의 고래 모양 아이콘이 정상 실행 중인지 확인하거나, 터미널에서 다음 명령어로 동작을 확인한다.  

```bash
docker info
```

- `docker`: Docker CLI(Command Line Interface / 명령줄 인터페이스) 제어 프로그램  
- `info`: Information (정보) / 현재 실행 중인 도커 엔진의 시스템 상태 및 정보 확인  

<br><br>

### 🟡 2) AI API Key 환경변수 등록  
터미널에서 사용할 AI 서비스의 인증 키를 환경변수로 등록한다. (실제 키 값은 소스 코드나 파일에 적지 않고 터미널 메모리에만 올린다.)  

```bash
export AI_API_KEY="본인의_실제_API_키"
export AI_API_FORMAT="openai"
export AI_MODEL="gpt-4o-mini"
```

- `export`: Export (내보내기) / 현재 터미널과 그 터미널이 실행할 자식 프로세스(Docker 등)에 환경변수를 전달  
- `AI_API_KEY`: AI Application Programming Interface Authentication Key / AI 서비스 인증 비밀키  
- `AI_API_FORMAT`: AI API 요청 및 응답 JSON 규격 (`openai` 또는 `anthropic`)  
- `AI_MODEL`: AI Model Identifier (식별자) / 호출하여 사용할 인공지능 모델 이름  

<br><br>

## 🟢 3. 단계별 Docker 사용 절차  

<br><br>

### 🟡 1단계: Docker 이미지 빌드 (Image Build)  

프로젝트 루트 폴더에 위치한 `Dockerfile`을 읽어 로컬 전용 실행 이미지를 제작한다.  

```bash
docker build -t ai-gitgen:local .
```

#### ⚫️ 명령어 및 옵션 해설 표  

| 항목 | 풀네임 (Full Name) | 상세 해설 |
| :--- | :--- | :--- |
| `docker` | Docker | 컨테이너 가상화 플랫폼 실행 명령어 |
| `build` | Build (만들다) | `Dockerfile`의 조리법을 읽어 독립된 실행 이미지(설계도)를 조립 |
| `-t` | Tag (이름표) | 생성할 이미지에 이름과 버전을 부여 (형식: `이름:태그`) |
| `ai-gitgen:local` | ai-gitgen:local | 생성할 이미지 이름(`ai-gitgen`)과 로컬 태그(`local`) 지정 |
| `.` | Current Working Directory | Dockerfile 및 복사 대상 파일이 위치한 현재 작업 디렉토리 전달 |

<br><br>

### 🟡 2단계: Git 커밋 메시지 자동 생성  

작업 중인 파일의 변경 사항(`git status`, `git diff`)을 읽어 AI가 규격에 맞는 커밋 메시지를 생성하도록 실행한다.  

```bash
docker run --rm -v "$PWD:/workspace:ro" -e AI_API_KEY -e AI_API_FORMAT -e AI_MODEL ai-gitgen:local commit
```

#### ⚫️ 명령어 및 옵션 해설 표  

| 옵션 / 인자 | 풀네임 (Full Name) | 상세 해설 |
| :--- | :--- | :--- |
| `run` | Run (실행하다) | 이미지를 바탕으로 새로운 격리 컨테이너를 가동 |
| `--rm` | Remove (삭제하다) | 작업이 끝나면 메모리와 디스크를 차지하지 않도록 1회용 컨테이너를 자동 파기 |
| `-v` | Volume (저장 공간 연결) | 호스트 컴퓨터의 폴더를 컨테이너 내부 특정 경로에 마운트(연결) |
| `$PWD` | Print Working Directory | 현재 내 작업 폴더의 전체 절대 경로를 나타내는 쉘 환경변수 |
| `/workspace` | Workspace (작업 공간) | 컨테이너 내부에서 소스 코드를 바라보게 될 대상 폴더 경로 |
| `:ro` | Read-Only (읽기 전용) | 컨테이너가 원본 코드를 임의로 고치거나 지우지 못하도록 안전하게 잠금 |
| `-e` | Environment Variable (환경변수) | 호스트 터미널에 등록해둔 환경변수를 컨테이너 안으로 통과시켜 전달 |
| `commit` | Commit Command | 컨테이너 내부의 `main.py`에 전달되는 커밋 메시지 생성 작업 명령 |

<br><br>

### 🟡 3단계: PR(Pull Request) 제목 및 본문 초안 생성  

브랜치 변경 내역을 요약하여 GitHub에 올릴 수 있는 PR 제목과 템플릿 본문(Why, What, How to Test)을 생성한다.  

```bash
docker run --rm -v "$PWD:/workspace:ro" -e AI_API_KEY -e AI_API_FORMAT -e AI_MODEL ai-gitgen:local pr
```

- 동작 원리는 커밋 명령과 동일하며, 마지막 인자로 `pr`을 주어 PR 초안 템플릿 형식으로 출력을 지시한다.  

<br><br>

### 🟡 4단계: Docker Compose를 활용한 간편 실행  

매번 길고 복잡한 `-v`, `-e` 옵션을 입력하기 번거로울 때, `compose.yaml` 파일에 저장된 설정을 통해 한 줄로 동일한 작업을 수행한다.  

```bash
# 1. Compose 기반 이미지 빌드
docker compose build

# 2. 커밋 메시지 생성 실행
docker compose run --rm ai-gitgen commit

# 3. PR 초안 생성 실행
docker compose run --rm ai-gitgen pr
```

#### ⚫️ 명령어 및 옵션 해설 표  

| 명령어 | 풀네임 (Full Name) | 상세 해설 |
| :--- | :--- | :--- |
| `compose` | Compose (구성하다) | 여러 실행 옵션과 서비스를 YAML 파일로 관리하는 Docker 공식 도구 |
| `build` | Build | `compose.yaml`에 명시된 설정에 따라 서비스 이미지를 일괄 빌드 |
| `run` | Run | compose 파일에 정의된 특정 서비스를 일회성 컨테이너로 가동 |
| `ai-gitgen` | Service Identifier | `compose.yaml` 파일 안에 정의해둔 작업 서비스의 고유 이름 |

<br><br>

### 🟡 5단계: 대화형 Bash 셸 접속 및 내부 환경 점검  

컨테이너가 어떤 운영체제인지, 내 파일들이 정상적으로 읽기 전용 연결되었는지 직접 두 눈으로 탐색할 때 사용한다.  

```bash
docker run --rm -it --entrypoint bash -v "$PWD:/workspace:ro" ai-gitgen:local
```

#### ⚫️ 명령어 및 옵션 해설 표  

| 옵션 | 풀네임 (Full Name) | 상세 해설 |
| :--- | :--- | :--- |
| `-i` | Interactive (대화형) | 사용자가 키보드로 치는 입력을 컨테이너 내부 프로그램으로 계속 전달 |
| `-t` | Pseudo-TTY (가상 터미널) | 사용자가 글자를 보고 명령을 칠 수 있는 깜빡이는 프롬프트 화면 창을 배정 |
| `--entrypoint bash` | Entry Point Replacement | 기본 실행 프로그램(`main.py`) 대신 `bash`(Bourne-Again SHell) 셸을 실행 |

#### ⚫️ 셸 내부 점검 명령어  

- `cat /etc/os-release`: concatenate / 파일 내용을 출력하여 Debian 12 리눅스임을 확인  
- `python --version`: 컨테이너 내부 Python 버전(3.12) 확인  
- `git --version`: 설치된 Git 버전 확인  
- `ls -la /workspace`: list all / 마운트된 프로젝트 파일 목록 확인  
- `exit`: exit / 컨테이너를 닫고 빠져나와 내 컴퓨터의 Mac 터미널로 복귀  

<br><br>

## 🟢 4. 문제 해결 및 오류 대응 (Troubleshooting)  

<br><br>

### 🟡 자주 발생하는 문제 및 해결 방법  

| 발생 증상 | 원인 분석 | 조치 방법 |
| :--- | :--- | :--- |
| `Cannot connect to the Docker daemon` | Docker Desktop 프로그램이 켜져 있지 않음 | Mac에서 Docker Desktop 애플리케이션을 실행하고 고래 아이콘이 켜진 후 재시도 |
| `[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다` | 호스트 터미널에 Key가 없거나 `-e AI_API_KEY` 전달 누락 | `export AI_API_KEY="내키"`를 먼저 실행한 뒤 도커 명령어에 `-e AI_API_KEY` 포함 |
| `fatal: not a git repository` | Git이 초기화되지 않은 폴더이거나 마운트 경로 오류 | 프로젝트 루트에서 `git init`이 되어 있는지 확인 후 `$PWD` 경로에서 명령 실행 |
| `Unknown command: bash` | `--entrypoint bash` 없이 뒤에 `bash`만 붙임 | Dockerfile의 ENTRYPOINT가 파이썬이므로 반드시 `--entrypoint bash` 옵션 사용 |

<br><br>

## 🟢 5. 자원 정리 (Resource Cleanup)  

실습을 모두 마치고 디스크 공간을 확보하고 싶을 때 이미지를 삭제한다.  

```bash
# 실습에서 만든 로컬 이미지 삭제
docker rmi ai-gitgen:local
```

- `rmi`: Remove Image (이미지 삭제) / 로컬 디스크에 저장된 `ai-gitgen:local` 이미지 파일을 제거  
