"""CLI가 각 모듈을 올바른 순서와 횟수로 연결하는지 검사한다."""  # 테스트 파일의 책임을 설명한다.

import contextlib  # 표준 출력과 오류를 문자열로 모은다.
import io  # 출력 캡처용 메모리 문자열 파일을 만든다.
import os  # 테스트 환경변수를 임시로 설정한다.
import unittest  # Python 기본 테스트 도구를 가져온다.
from unittest.mock import patch  # Git 수집과 API 호출을 가짜 함수로 바꾼다.

from ai_gitgen.cli import main  # 실제 CLI 진입점을 가져온다.
from ai_gitgen.models import GitContext  # 테스트용 Git 맥락을 만든다.


def changed_context() -> GitContext:  # 반복 사용할 변경 있음 맥락을 만든다.
    return GitContext("main", ("main.py",), "M  main.py", "diff --git a/main.py b/main.py\n+change", 2, 1, (), False)  # 외부 정보가 없는 작은 가짜 변경을 돌려준다.


def empty_context() -> GitContext:  # 반복 사용할 변경 없음 맥락을 만든다.
    return GitContext("", (), "", "", 0, 0, (), False)  # 모든 변경 값이 빈 맥락을 돌려준다.


class CliTest(unittest.TestCase):  # 전체 CLI 연결 동작 검사를 묶는다.
    def capture(self, arguments: list[str]) -> tuple[int, str, str]:  # CLI 종료 번호와 두 출력을 함께 모은다.
        stdout = io.StringIO()  # 표준 출력을 받을 메모리 파일을 만든다.
        stderr = io.StringIO()  # 표준 오류를 받을 메모리 파일을 만든다.
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):  # 터미널 출력을 메모리 파일로 잠시 돌린다.
            code = main(arguments)  # 전달된 CLI 인자로 프로그램을 실행한다.
        return code, stdout.getvalue(), stderr.getvalue()  # 종료 번호와 모은 출력을 돌려준다.

    @patch("ai_gitgen.cli.generate_text")  # 실제 API 호출을 가짜 함수로 바꾼다.
    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_no_changes_skips_api(self, collect: object, generate: object) -> None:  # 변경 없을 때 API를 부르지 않는지 검사한다.
        collect.return_value = empty_context()  # Git 수집 결과를 변경 없음으로 설정한다.
        code, stdout, stderr = self.capture(["commit"])  # commit 명령을 실행하고 출력을 모은다.
        self.assertEqual(code, 0)  # 변경 없음은 정상 종료여야 한다.
        self.assertIn("변경 사항이 없습니다", stdout)  # 사용자가 종료 이유를 확인할 수 있어야 한다.
        self.assertEqual(stderr, "")  # 오류 출력은 없어야 한다.
        generate.assert_not_called()  # 비용이 드는 API는 호출하지 않아야 한다.

    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_missing_api_key_fails(self, collect: object) -> None:  # API Key 누락 오류를 검사한다.
        collect.return_value = changed_context()  # API가 필요한 변경 있음 상태를 만든다.
        with patch.dict(os.environ, {}, clear=True):  # 현재 환경변수를 테스트 동안 모두 비운다.
            code, stdout, stderr = self.capture(["commit"])  # commit 명령을 실행하고 출력을 모은다.
        self.assertEqual(code, 2)  # 설정 오류 종료 번호여야 한다.
        self.assertIn("AI_API_KEY", stderr)  # 필요한 환경변수 이름을 안내해야 한다.
        self.assertNotIn("Traceback", stderr)  # 초보자에게 불필요한 내부 traceback은 없어야 한다.
        self.assertIn("Git status 수집 완료", stdout)  # API 전 단계인 Git 수집은 완료됐음을 보여야 한다.

    @patch("ai_gitgen.cli.generate_text")  # 실제 API 호출을 가짜 커밋 응답으로 바꾼다.
    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_commit_calls_api_once(self, collect: object, generate: object) -> None:  # 커밋 생성의 호출 횟수와 출력을 검사한다.
        collect.return_value = changed_context()  # 변경 있음 상태를 만든다.
        generate.return_value = "feat: 자동 생성 추가\n\n- main.py 변경"  # 가짜 AI 커밋 응답을 준비한다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key"}, clear=True):  # 테스트용 가짜 키만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["commit", "-temperature", "0.1", "-max-tokens", "400"])  # 옵션을 바꿔 명령을 실행한다.
        self.assertEqual(code, 0)  # 성공 종료여야 한다.
        self.assertEqual(stderr, "")  # 오류 출력은 없어야 한다.
        self.assertIn("=== Commit Message ===", stdout)  # 결과 시작 헤더가 있어야 한다.
        self.assertIn("feat: 자동 생성 추가", stdout)  # AI 커밋 제목이 출력되어야 한다.
        self.assertEqual(generate.call_count, 1)  # API는 정확히 한 번만 호출되어야 한다.
        settings = generate.call_args.args[0]  # API 함수에 전달된 설정을 꺼낸다.
        self.assertEqual(settings.temperature, 0.1)  # 바꾼 temperature가 전달되어야 한다.
        self.assertEqual(settings.max_tokens, 400)  # 바꾼 max_tokens가 전달되어야 한다.

    @patch("ai_gitgen.cli.generate_text")  # 실제 API 호출을 가짜 PR 응답으로 바꾼다.
    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_pr_output_has_required_sections(self, collect: object, generate: object) -> None:  # PR 출력의 필수 구조를 검사한다.
        collect.return_value = changed_context()  # 변경 있음 상태를 만든다.
        generate.return_value = '{"title":"feat: PR 생성","body":"## Why\\n- 이유\\n\\n## What\\n- 변경\\n\\n## How to Test\\n- 확인"}'  # 가짜 AI PR JSON을 준비한다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key"}, clear=True):  # 테스트용 가짜 키만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["pr"])  # pr 명령을 실행하고 출력을 모은다.
        self.assertEqual(code, 0)  # 성공 종료여야 한다.
        self.assertEqual(stderr, "")  # 오류 출력은 없어야 한다.
        self.assertIn("=== PR Title ===", stdout)  # PR 제목 구획이 있어야 한다.
        self.assertIn("## Why\n- 이유", stdout)  # Why 섹션과 불릿이 있어야 한다.
        self.assertIn("## What\n- 변경", stdout)  # What 섹션과 불릿이 있어야 한다.
        self.assertIn("## How to Test\n- 확인", stdout)  # How to Test 섹션과 불릿이 있어야 한다.
        self.assertEqual(generate.call_count, 1)  # API는 정확히 한 번만 호출되어야 한다.

    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_deceptive_localhost_url_is_rejected(self, collect: object) -> None:  # localhost처럼 보이는 외부 주소를 막는지 검사한다.
        collect.return_value = changed_context()  # API 설정 검사까지 진행할 변경 있음 상태를 만든다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key"}, clear=True):  # 테스트용 가짜 Key만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["commit", "-api-url", "http://localhost.evil.example/v1"])  # 위장 호스트로 실행을 시도한다.
        self.assertEqual(code, 2)  # 안전하지 않은 URL은 오류 종료여야 한다.
        self.assertIn("HTTPS", stderr)  # 사용자가 HTTPS 조건을 확인할 수 있어야 한다.
        self.assertIn("Git status 수집 완료", stdout)  # API 요청 전 Git 수집까지만 진행돼야 한다.

    @patch("ai_gitgen.cli.collect_git_context")  # 실제 Git 수집을 가짜 함수로 바꾼다.
    def test_anthropic_temperature_range(self, collect: object) -> None:  # Anthropic temperature 상한을 검사한다.
        collect.return_value = changed_context()  # API 설정 검사까지 진행할 변경 있음 상태를 만든다.
        with patch.dict(os.environ, {"AI_API_KEY": "fake-key"}, clear=True):  # 테스트용 가짜 Key만 환경변수에 넣는다.
            code, stdout, stderr = self.capture(["commit", "-api-format", "anthropic", "-temperature", "1.5"])  # 허용 범위를 넘는 값으로 실행한다.
        self.assertEqual(code, 2)  # 제공자 설정 오류 종료여야 한다.
        self.assertIn("1.0", stderr)  # Anthropic 상한을 사용자에게 알려야 한다.
        self.assertIn("Git status 수집 완료", stdout)  # API 요청 전 Git 수집까지만 진행돼야 한다.


if __name__ == "__main__":  # 이 테스트 파일을 직접 실행했는지 확인한다.
    unittest.main()  # 파일 안의 모든 테스트를 실행한다.
