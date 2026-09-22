# Python 3.12가 포함된 작은 Debian 기반 이미지를 시작점으로 사용한다.
FROM python:3.12-slim

# Git 상태와 diff를 읽기 위해 Git을 설치하고 패키지 목록 캐시를 바로 지운다.
RUN apt-get update && apt-get install --yes --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# 프로그램 파일을 둘 컨테이너 내부 폴더를 작업 위치로 정한다.
WORKDIR /app

# 패키지 설정과 실행 파일을 이미지 안으로 복사한다.
COPY pyproject.toml main.py ./

# 실제 기능이 들어 있는 Python 패키지를 이미지 안으로 복사한다.
COPY ai_gitgen ./ai_gitgen

# 읽기 전용으로 연결할 저장소의 정확한 위치만 Git 안전 경로로 등록한다.
RUN git config --system --add safe.directory /workspace

# 컨테이너가 프로젝트 Git 저장소를 읽을 기본 위치를 정한다.
WORKDIR /workspace

# 컨테이너 뒤에 적은 commit 또는 pr을 Python 프로그램에 전달한다.
ENTRYPOINT ["python", "/app/main.py"]

# 별도 명령이 없으면 도움말을 출력한다.
CMD ["--help"]
