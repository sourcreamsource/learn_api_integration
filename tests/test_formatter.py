"""AI 응답 후처리와 최종 형식 검증을 검사한다."""  # 테스트 파일의 책임을 설명한다.

import json  # PR 테스트용 JSON 문자열을 만든다.
import unittest  # Python 기본 테스트 도구를 가져온다.

from ai_gitgen.errors import OutputFormatError  # 빈 응답 오류를 확인하기 위해 가져온다.
from ai_gitgen.formatter import format_commit_message, format_pr_draft, validate_pr_draft  # 검사할 후처리 함수를 가져온다.


class CommitFormatterTest(unittest.TestCase):  # 커밋 메시지 후처리 검사를 묶는다.
    def test_commit_title_is_limited_to_72_characters(self) -> None:  # 너무 긴 제목이 잘리는지 검사한다.
        raw = "feat(core): " + ("긴제목" * 40) + "\n\n- 변경 내용을 추가"  # 72자를 넘는 가짜 응답을 만든다.
        formatted = format_commit_message(raw)  # 커밋 메시지 후처리를 실행한다.
        title = formatted.splitlines()[0]  # 첫 줄 제목만 꺼낸다.
        self.assertLessEqual(len(title), 72)  # 제목이 최대 72자여야 한다.
        self.assertIn("- 변경 내용을 추가", formatted)  # 본문은 유지되어야 한다.

    def test_commit_code_fence_and_label_are_removed(self) -> None:  # 불필요한 장식이 제거되는지 검사한다.
        raw = "```text\nCommit Message:\nfeat: 기능 추가\n\n- 파일 변경\n```"  # 흔한 AI 응답 장식을 포함한 예시를 만든다.
        formatted = format_commit_message(raw)  # 후처리를 실행한다.
        self.assertTrue(formatted.startswith("feat: 기능 추가"))  # 실제 제목부터 시작해야 한다.
        self.assertNotIn("```", formatted)  # 코드 울타리가 없어야 한다.

    def test_empty_commit_response_fails(self) -> None:  # 빈 AI 응답을 성공 처리하지 않는지 검사한다.
        with self.assertRaises(OutputFormatError):  # 지정 오류가 발생해야 통과시킨다.
            format_commit_message("   ")  # 공백뿐인 응답을 처리한다.


class PullRequestFormatterTest(unittest.TestCase):  # PR 초안 후처리 검사를 묶는다.
    def test_valid_json_pr_is_normalized(self) -> None:  # 정상 JSON이 요구 형식으로 정리되는지 검사한다.
        raw = json.dumps({"title": "feat: 자동 생성 추가", "body": "## Why\n* 필요함\n\n## What\n+ 기능 추가\n\n## How to Test\n- 실행 확인"}, ensure_ascii=False)  # 여러 불릿 기호를 섞은 JSON 응답을 만든다.
        draft = format_pr_draft(raw)  # PR 초안을 정리한다.
        validate_pr_draft(draft)  # 최종 검증에서도 통과해야 한다.
        self.assertEqual(draft.title, "feat: 자동 생성 추가")  # 제목 내용이 유지되어야 한다.
        self.assertIn("## Why\n- 필요함", draft.body)  # Why 불릿이 하이픈 형식이어야 한다.
        self.assertIn("## What\n- 기능 추가", draft.body)  # What 불릿이 하이픈 형식이어야 한다.
        self.assertIn("## How to Test\n- 실행 확인", draft.body)  # 테스트 불릿이 유지되어야 한다.

    def test_missing_sections_receive_safe_fallbacks(self) -> None:  # 필수 섹션 누락을 후처리하는지 검사한다.
        raw = json.dumps({"title": "docs: 문서 정리", "body": "설명만 있음"}, ensure_ascii=False)  # 섹션이 전혀 없는 응답을 만든다.
        draft = format_pr_draft(raw)  # 누락 섹션 보완을 실행한다.
        validate_pr_draft(draft)  # 보완된 결과가 모든 규칙을 만족해야 한다.
        self.assertEqual(draft.body.count("## "), 3)  # 필수 헤더가 정확히 세 개여야 한다.
        self.assertGreaterEqual(draft.body.count("- "), 3)  # 각 섹션에 불릿이 하나 이상 있어야 한다.

    def test_pr_title_is_one_line_and_limited(self) -> None:  # PR 제목의 줄 수와 길이를 검사한다.
        raw = json.dumps({"title": ("긴 제목 " * 30) + "\n두 번째 줄", "body": ""}, ensure_ascii=False)  # 길고 여러 줄인 제목을 만든다.
        draft = format_pr_draft(raw)  # 제목 후처리를 실행한다.
        self.assertNotIn("\n", draft.title)  # 제목에 줄바꿈이 없어야 한다.
        self.assertLessEqual(len(draft.title), 80)  # 제목이 최대 80자여야 한다.


if __name__ == "__main__":  # 이 테스트 파일을 직접 실행했는지 확인한다.
    unittest.main()  # 파일 안의 모든 테스트를 실행한다.
