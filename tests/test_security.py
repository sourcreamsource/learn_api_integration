"""민감정보 보호와 전송량 제한을 검사한다."""  # 테스트 파일의 책임을 설명한다.

import unittest  # Python 기본 테스트 도구를 가져온다.

from ai_gitgen.security import is_protected_path, limit_diff_lines, mask_sensitive_text  # 검사할 보안 함수를 가져온다.


class SecurityTest(unittest.TestCase):  # 보안 동작을 묶어 검사한다.
    def test_protected_paths_are_blocked(self) -> None:  # 비밀 파일 경로가 차단되는지 검사한다.
        protected = [".env", ".env.local", "_temporary/models.json", "cert/private.key", "credentials.json", "AGENTS.md", ".agents/local.md", ".codex/settings.json"]  # 대표적인 비밀 파일 경로를 준비한다.
        for path in protected:  # 각 경로를 하나씩 확인한다.
            with self.subTest(path=path):  # 실패 시 어떤 경로인지 보여 주도록 하위 테스트를 만든다.
                self.assertTrue(is_protected_path(path))  # 보호 대상이라고 판단해야 통과시킨다.

    def test_normal_source_path_is_allowed(self) -> None:  # 일반 소스 파일은 허용되는지 검사한다.
        self.assertFalse(is_protected_path("ai_gitgen/cli.py"))  # 정상 Python 파일은 차단하지 않아야 한다.

    def test_sensitive_values_are_masked(self) -> None:  # 알려진 민감정보 모양이 가려지는지 검사한다.
        source = "api_key=secret-value\nAuthorization: Bearer token.value\nuser@example.com\npassword=hunter2\n/Users/private-name/project"  # 실제 비밀이 아닌 가짜 예시를 준비한다.
        masked = mask_sensitive_text(source)  # 보안 마스킹을 적용한다.
        self.assertNotIn("secret-value", masked)  # 가짜 API Key 원문이 없어야 한다.
        self.assertNotIn("token.value", masked)  # 가짜 Bearer 토큰 원문이 없어야 한다.
        self.assertNotIn("user@example.com", masked)  # 이메일 원문이 없어야 한다.
        self.assertNotIn("hunter2", masked)  # 가짜 비밀번호 원문이 없어야 한다.
        self.assertNotIn("private-name", masked)  # 사용자 계정 이름이 경로에 남지 않아야 한다.
        self.assertIn("MASKED", masked)  # 마스킹됐다는 표시는 남아야 한다.

    def test_diff_line_limit(self) -> None:  # 최대 diff 줄 수 제한을 검사한다.
        source = "\n".join(f"line-{number}" for number in range(205))  # 205줄짜리 가짜 diff를 만든다.
        limited, was_truncated = limit_diff_lines(source, max_lines=200)  # 200줄 제한을 적용한다.
        self.assertTrue(was_truncated)  # 잘림 표시가 참이어야 한다.
        self.assertEqual(len(limited.splitlines()), 201)  # 200줄과 안내 1줄만 남아야 한다.
        self.assertIn("5줄 생략", limited)  # 생략된 줄 수를 정확히 알려야 한다.


if __name__ == "__main__":  # 이 테스트 파일을 직접 실행했는지 확인한다.
    unittest.main()  # 파일 안의 모든 테스트를 실행한다.
