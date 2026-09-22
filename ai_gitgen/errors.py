"""사용자에게 안전하게 보여 줄 프로그램 오류를 정의한다."""  # 파일의 책임을 설명한다.


class AppError(Exception):  # 예상 가능한 오류의 공통 부모 클래스를 만든다.
    """CLI가 메시지만 보여 주고 종료해도 되는 오류다."""  # 오류의 의미를 설명한다.


class GitRepositoryError(AppError):  # Git 사용 위치가 잘못됐을 때 쓸 오류를 만든다.
    """현재 위치에서 Git 정보를 안전하게 모을 수 없을 때 발생한다."""  # 발생 조건을 설명한다.


class ApiConfigurationError(AppError):  # API 설정이 빠졌을 때 쓸 오류를 만든다.
    """API Key 같은 필수 설정이 없을 때 발생한다."""  # 발생 조건을 설명한다.


class ApiRequestError(AppError):  # API 통신이 실패했을 때 쓸 오류를 만든다.
    """네트워크, 인증, 응답 형식 문제로 API 호출이 실패할 때 발생한다."""  # 발생 조건을 설명한다.


class OutputFormatError(AppError):  # AI 응답을 읽을 수 없을 때 쓸 오류를 만든다.
    """AI 응답에 사용할 텍스트가 없을 때 발생한다."""  # 발생 조건을 설명한다.
