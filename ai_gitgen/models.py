"""모듈 사이에서 주고받는 데이터 구조를 정의한다."""  # 파일의 책임을 설명한다.

from dataclasses import dataclass  # 관련 값을 묶는 dataclass 기능을 가져온다.


@dataclass(frozen=True)  # 생성 후 실수로 값이 바뀌지 않는 데이터 묶음을 만든다.
class GitContext:  # Git에서 수집한 정보를 한 객체에 담는다.
    branch: str  # 현재 브랜치 이름을 저장한다.
    changed_files: tuple[str, ...]  # 전송 대상이 된 변경 파일 목록을 저장한다.
    status_text: str  # 정리된 Git 상태 내용을 저장한다.
    diff_text: str  # AI에 보낼 변경 내용을 저장한다.
    diff_line_count: int  # 실제로 담긴 diff 줄 수를 저장한다.
    total_changed_count: int  # Git이 감지한 전체 변경 파일 수를 저장한다.
    excluded_files: tuple[str, ...]  # 보안 정책이나 개수 제한으로 제외한 파일을 저장한다.
    was_truncated: bool  # 안전 모드에서 내용이 잘렸는지를 저장한다.


@dataclass(frozen=True)  # API 요청 설정도 실행 중 바뀌지 않게 만든다.
class ApiSettings:  # AI API 호출에 필요한 설정을 한 객체에 담는다.
    api_key: str  # 환경변수에서 읽은 비밀 인증 키를 저장한다.
    api_url: str  # 요청을 보낼 전체 URL을 저장한다.
    api_format: str  # openai 또는 anthropic 요청 형식을 저장한다.
    model: str  # 사용할 모델 ID를 저장한다.
    temperature: float  # 결과의 표현 다양성을 조절하는 값을 저장한다.
    max_tokens: int  # AI가 만들 수 있는 최대 토큰 수를 저장한다.
    timeout: float  # 네트워크 요청 최대 대기 시간을 초 단위로 저장한다.


@dataclass(frozen=True)  # PR 제목과 본문이 함께 움직이도록 묶는다.
class PullRequestDraft:  # 정리와 검증을 마친 PR 초안을 나타낸다.
    title: str  # 최대 80자인 PR 제목을 저장한다.
    body: str  # 필수 세 섹션이 들어간 PR 본문을 저장한다.
