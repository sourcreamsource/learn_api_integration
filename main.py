"""프로젝트 루트에서 CLI(Command Line Interface)를 시작하는 파일이다."""  # 이 파일의 역할을 설명한다.

from ai_gitgen.cli import main  # 실제 명령 처리 함수만 가져온다.


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만 아래 코드를 실행한다.
    raise SystemExit(main())  # CLI 종료 번호를 운영체제에 전달하며 프로그램을 끝낸다.
