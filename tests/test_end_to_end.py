"""로컬 HTTP 서버로 CLI 전체 경로를 종단 간 검사한다."""  # 테스트 파일의 책임을 설명한다.

import contextlib  # CLI 표준 출력을 문자열로 모은다.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # 로컬 전용 가짜 AI HTTP 서버를 만든다.
import io  # 출력 캡처용 메모리 문자열 파일을 만든다.
import json  # HTTP 요청과 응답의 JSON을 처리한다.
import os  # 테스트 환경변수와 현재 폴더를 바꾼다.
from pathlib import Path  # 임시 저장소 파일 경로를 다룬다.
import subprocess  # 임시 저장소에 Git 명령을 실행한다.
import tempfile  # 테스트가 끝나면 사라지는 저장소를 만든다.
import threading  # 로컬 HTTP 서버를 테스트와 동시에 실행한다.
import unittest  # Python 기본 테스트 도구를 가져온다.
from unittest.mock import patch  # API Key 환경변수를 테스트 동안만 설정한다.

from ai_gitgen.cli import main  # 실제 CLI 진입점을 가져온다.


class FakeAiHandler(BaseHTTPRequestHandler):  # AI API처럼 POST 요청을 받는 로컬 처리기를 만든다.
    call_count = 0  # 서버가 받은 요청 횟수를 클래스에 기록한다.

    def do_POST(self) -> None:  # HTTP POST 요청을 받았을 때 실행한다.
        type(self).call_count += 1  # 실제로 받은 요청 횟수를 1 늘린다.
        length = int(self.headers.get("Content-Length", "0"))  # 요청 본문 크기를 헤더에서 읽는다.
        request_body = json.loads(self.rfile.read(length).decode("utf-8"))  # 요청 JSON을 Python 값으로 바꾼다.
        prompt = request_body["messages"][-1]["content"]  # 마지막 user 메시지에서 프롬프트를 꺼낸다.
        if "PR 제목" in prompt:  # PR 생성 요청인지 확인한다.
            generated = '{"title":"feat: 로컬 종단 간 검증","body":"## Why\\n- 전체 흐름 확인\\n\\n## What\\n- 로컬 서버 연결\\n\\n## How to Test\\n- 자동 테스트 실행"}'  # PR 규칙을 만족하는 가짜 AI 텍스트를 만든다.
        else:  # 커밋 메시지 생성 요청을 처리한다.
            generated = "test(cli): 로컬 종단 간 흐름 검증\n\n- Git 수집부터 출력까지 확인"  # 커밋 규칙을 만족하는 가짜 AI 텍스트를 만든다.
        response_body = json.dumps({"choices": [{"message": {"content": generated}}]}, ensure_ascii=False).encode("utf-8")  # OpenAI 호환 응답 JSON을 만든다.
        self.send_response(200)  # HTTP 성공 상태 코드를 보낸다.
        self.send_header("Content-Type", "application/json; charset=utf-8")  # 응답 데이터 종류와 문자 인코딩을 알린다.
        self.send_header("Content-Length", str(len(response_body)))  # 클라이언트가 읽을 응답 크기를 알린다.
        self.end_headers()  # HTTP 응답 헤더 작성을 끝낸다.
        self.wfile.write(response_body)  # 가짜 AI JSON 응답 본문을 보낸다.

    def log_message(self, format_text: str, *args: object) -> None:  # 기본 서버 접근 로그 출력을 덮어쓴다.
        return None  # 테스트 출력이 불필요한 로그로 섞이지 않게 아무것도 하지 않는다.


def run_git(folder: Path, *arguments: str) -> None:  # 임시 저장소 설정용 Git 명령을 실행한다.
    subprocess.run(["git", *arguments], cwd=folder, capture_output=True, text=True, check=True)  # Git 실패 시 테스트도 즉시 실패하게 한다.


class EndToEndTest(unittest.TestCase):  # 로컬 네트워크를 포함한 전체 흐름 검사를 묶는다.
    def setUp(self) -> None:  # 각 테스트 전에 Git 저장소와 HTTP 서버를 준비한다.
        self.original_cwd = Path.cwd()  # 테스트 뒤 돌아갈 원래 폴더를 저장한다.
        try:  # 실행 환경이 로컬 소켓 생성을 허용하는지 먼저 확인한다.
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAiHandler)  # 사용 가능한 임의 포트에 로컬 서버를 연다.
        except PermissionError:  # 격리 정책이 로컬 소켓도 금지한 경우를 처리한다.
            self.skipTest("현재 실행 환경이 로컬 HTTP 소켓 생성을 허용하지 않습니다.")  # 다른 테스트를 실패시키지 않고 제한을 명확히 기록한다.
        self.temporary = tempfile.TemporaryDirectory()  # 자동 삭제되는 임시 폴더를 만든다.
        self.root = Path(self.temporary.name)  # 임시 폴더 문자열을 Path 객체로 바꾼다.
        run_git(self.root, "init", "-q", "-b", "main")  # main 브랜치의 테스트 Git 저장소를 만든다.
        run_git(self.root, "config", "user.email", "tester@example.test")  # 테스트 저장소에만 가짜 이메일을 설정한다.
        run_git(self.root, "config", "user.name", "Test User")  # 테스트 저장소에만 가짜 사용자 이름을 설정한다.
        source = self.root / "example.txt"  # 변경을 만들 테스트 파일 경로를 정한다.
        source.write_text("before\n", encoding="utf-8")  # 첫 커밋용 파일 내용을 작성한다.
        run_git(self.root, "add", "example.txt")  # 테스트 파일을 스테이징한다.
        run_git(self.root, "commit", "-q", "-m", "test: initial")  # 비교 기준 커밋을 만든다.
        source.write_text("before\nafter\n", encoding="utf-8")  # AI 입력으로 쓸 실제 Git 변경을 만든다.
        os.chdir(self.root)  # 실제 CLI가 임시 저장소 루트에서 실행되게 한다.
        FakeAiHandler.call_count = 0  # 이전 테스트의 요청 횟수를 초기화한다.
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)  # 서버를 백그라운드에서 실행할 스레드를 만든다.
        self.thread.start()  # 로컬 가짜 AI 서버 실행을 시작한다.
        self.api_url = f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions"  # CLI에 전달할 로컬 API 전체 주소를 만든다.

    def tearDown(self) -> None:  # 각 테스트 뒤 서버와 임시 저장소를 정리한다.
        self.server.shutdown()  # 로컬 HTTP 서버가 새 요청을 받지 않게 멈춘다.
        self.server.server_close()  # 서버가 사용한 소켓을 닫는다.
        self.thread.join(timeout=2)  # 백그라운드 서버 스레드가 끝날 때까지 짧게 기다린다.
        os.chdir(self.original_cwd)  # 임시 폴더 삭제 전에 원래 폴더로 돌아간다.
        self.temporary.cleanup()  # 임시 Git 저장소를 삭제한다.

    def run_cli(self, command: str) -> tuple[int, str]:  # 실제 CLI를 로컬 서버에 연결해 실행한다.
        stdout = io.StringIO()  # CLI 표준 출력을 받을 메모리 파일을 만든다.
        stderr = io.StringIO()  # CLI 표준 오류를 받을 메모리 파일을 만든다.
        arguments = [command, "-api-url", self.api_url, "-api-format", "openai", "-model", "local-test-model"]  # 로컬 가짜 서버용 CLI 인자를 준비한다.
        with patch.dict(os.environ, {"AI_API_KEY": "local-fake-key"}, clear=True):  # 외부에서 쓸 수 없는 가짜 Key만 환경변수에 넣는다.
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):  # CLI 출력을 메모리로 잠시 돌린다.
                code = main(arguments)  # Git 수집부터 HTTP 요청과 출력까지 실제 흐름을 실행한다.
        self.assertEqual(stderr.getvalue(), "")  # 정상 흐름에는 오류 출력이 없어야 한다.
        return code, stdout.getvalue()  # 종료 번호와 표준 출력을 돌려준다.

    def test_commit_full_flow(self) -> None:  # 커밋 명령의 전체 흐름을 검사한다.
        code, output = self.run_cli("commit")  # 실제 Git과 로컬 HTTP 서버로 commit을 실행한다.
        self.assertEqual(code, 0)  # 성공 종료 번호여야 한다.
        self.assertEqual(FakeAiHandler.call_count, 1)  # HTTP 요청은 정확히 한 번이어야 한다.
        self.assertIn("=== Commit Message ===", output)  # 최종 커밋 출력 구획이 있어야 한다.
        self.assertIn("test(cli): 로컬 종단 간 흐름 검증", output)  # 로컬 서버의 생성 결과가 출력되어야 한다.

    def test_pr_full_flow(self) -> None:  # PR 명령의 전체 흐름을 검사한다.
        code, output = self.run_cli("pr")  # 실제 Git과 로컬 HTTP 서버로 pr을 실행한다.
        self.assertEqual(code, 0)  # 성공 종료 번호여야 한다.
        self.assertEqual(FakeAiHandler.call_count, 1)  # HTTP 요청은 정확히 한 번이어야 한다.
        self.assertIn("=== PR Title ===", output)  # 최종 PR 제목 구획이 있어야 한다.
        self.assertIn("## Why\n- 전체 흐름 확인", output)  # Why 섹션과 불릿이 출력되어야 한다.
        self.assertIn("## What\n- 로컬 서버 연결", output)  # What 섹션과 불릿이 출력되어야 한다.
        self.assertIn("## How to Test\n- 자동 테스트 실행", output)  # 테스트 섹션과 불릿이 출력되어야 한다.


if __name__ == "__main__":  # 이 테스트 파일을 직접 실행했는지 확인한다.
    unittest.main()  # 파일 안의 모든 테스트를 실행한다.
