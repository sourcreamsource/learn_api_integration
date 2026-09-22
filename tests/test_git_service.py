"""실제 임시 Git 저장소에서 변경 사항 수집을 검사한다."""  # 테스트 파일의 책임을 설명한다.

import os  # 테스트 동안 현재 폴더를 바꾼다.
from pathlib import Path  # 임시 파일 경로를 다룬다.
import subprocess  # 임시 저장소에 Git 명령을 실행한다.
import tempfile  # 테스트가 끝나면 사라지는 폴더를 만든다.
import unittest  # Python 기본 테스트 도구를 가져온다.

from ai_gitgen.errors import GitRepositoryError  # 위치 오류를 확인하기 위해 가져온다.
from ai_gitgen.git_service import collect_git_context  # 검사할 Git 수집 함수를 가져온다.


def run_git(folder: Path, *arguments: str) -> None:  # 임시 저장소 설정용 Git 명령을 실행한다.
    subprocess.run(["git", *arguments], cwd=folder, capture_output=True, text=True, check=True)  # 실패하면 테스트도 즉시 실패하게 한다.


class GitServiceTest(unittest.TestCase):  # 실제 Git 수집 동작 검사를 묶는다.
    def setUp(self) -> None:  # 각 테스트 전에 독립 저장소를 준비한다.
        self.original_cwd = Path.cwd()  # 테스트가 끝난 뒤 돌아갈 원래 위치를 저장한다.
        self.temporary = tempfile.TemporaryDirectory()  # 자동 삭제되는 임시 폴더를 만든다.
        self.root = Path(self.temporary.name)  # 문자열 경로를 Path 객체로 바꾼다.
        run_git(self.root, "init", "-q", "-b", "main")  # main 브랜치로 빈 Git 저장소를 만든다.
        run_git(self.root, "config", "user.email", "tester@example.test")  # 테스트 저장소에만 가짜 이메일을 설정한다.
        run_git(self.root, "config", "user.name", "Test User")  # 테스트 저장소에만 가짜 이름을 설정한다.
        (self.root / "tracked.txt").write_text("first\n", encoding="utf-8")  # 첫 커밋에 들어갈 일반 파일을 만든다.
        run_git(self.root, "add", "tracked.txt")  # 일반 파일을 스테이징 영역에 올린다.
        run_git(self.root, "commit", "-q", "-m", "test: initial")  # 비교 기준이 될 첫 커밋을 만든다.
        os.chdir(self.root)  # 수집 함수가 임시 저장소 루트에서 실행되게 한다.

    def tearDown(self) -> None:  # 각 테스트 뒤에 환경을 원래대로 되돌린다.
        os.chdir(self.original_cwd)  # 삭제 전에 임시 폴더 밖으로 이동한다.
        self.temporary.cleanup()  # 테스트 파일과 Git 저장소를 모두 삭제한다.

    def test_no_changes_returns_empty_context(self) -> None:  # 변경이 없을 때 API용 맥락이 비는지 검사한다.
        context = collect_git_context()  # 깨끗한 저장소의 변경 정보를 수집한다.
        self.assertEqual(context.total_changed_count, 0)  # 변경 파일 수가 0이어야 한다.
        self.assertEqual(context.diff_text, "")  # diff 내용이 비어야 한다.

    def test_tracked_and_untracked_changes_are_collected(self) -> None:  # 수정 파일과 새 파일을 모두 수집하는지 검사한다.
        (self.root / "tracked.txt").write_text("first\nsecond\n", encoding="utf-8")  # 추적 파일 내용을 수정한다.
        (self.root / "new.txt").write_text("new content\n", encoding="utf-8")  # Git이 아직 추적하지 않는 파일을 만든다.
        context = collect_git_context()  # 변경 정보를 수집한다.
        self.assertEqual(context.total_changed_count, 2)  # 두 변경 파일을 모두 감지해야 한다.
        self.assertEqual(set(context.changed_files), {"tracked.txt", "new.txt"})  # 두 파일이 전송 대상이어야 한다.
        self.assertIn(" M tracked.txt", context.status_text)  # 수정 파일의 실제 작업 트리 상태 코드가 있어야 한다.
        self.assertIn("?? new.txt", context.status_text)  # 새 파일의 실제 미추적 상태 코드가 있어야 한다.
        self.assertIn("+second", context.diff_text)  # 추적 파일의 추가 줄이 diff에 있어야 한다.
        self.assertIn("+new content", context.diff_text)  # 새 파일 내용도 git diff 형태로 있어야 한다.

    def test_protected_file_content_is_excluded(self) -> None:  # 비밀 파일 내용이 diff에서 빠지는지 검사한다.
        secret_folder = self.root / "_temporary"  # 보호 대상 폴더 경로를 만든다.
        secret_folder.mkdir()  # 실제 보호 대상 폴더를 만든다.
        (secret_folder / "models.json").write_text("do-not-send", encoding="utf-8")  # 가짜 비밀 설정 파일을 만든다.
        context = collect_git_context()  # 변경 정보를 수집한다.
        self.assertEqual(context.total_changed_count, 1)  # Git 변경 자체는 감지해야 한다.
        self.assertEqual(context.changed_files, ())  # AI 전송 대상에는 포함하지 않아야 한다.
        self.assertNotIn("do-not-send", context.diff_text)  # 비밀 파일 내용이 diff에 없어야 한다.
        self.assertEqual(context.excluded_files, ("_temporary/models.json",))  # 제외된 경로를 내부 상태로 기록해야 한다.

    def test_subdirectory_execution_fails(self) -> None:  # 저장소 하위 폴더 실행을 막는지 검사한다.
        child = self.root / "child"  # 하위 폴더 경로를 만든다.
        child.mkdir()  # 실제 하위 폴더를 만든다.
        os.chdir(child)  # 저장소 루트가 아닌 하위 폴더로 이동한다.
        with self.assertRaises(GitRepositoryError):  # 실행 위치 오류가 발생해야 통과시킨다.
            collect_git_context()  # 잘못된 위치에서 수집을 시도한다.

    def test_safe_mode_limits_file_count(self) -> None:  # 안전 모드가 최대 10개 파일만 선택하는지 검사한다.
        for number in range(12):  # 제한보다 두 개 많은 새 파일을 만든다.
            (self.root / f"new-{number:02d}.txt").write_text(f"line {number}\n", encoding="utf-8")  # 서로 다른 내용의 새 파일을 작성한다.
        context = collect_git_context(safe_mode=True)  # 기본 안전 모드로 변경 정보를 수집한다.
        self.assertEqual(context.total_changed_count, 12)  # Git은 전체 12개 변경을 감지해야 한다.
        self.assertEqual(len(context.changed_files), 10)  # AI 전송 대상은 최대 10개여야 한다.
        self.assertEqual(len(context.excluded_files), 2)  # 나머지 두 파일은 제한으로 제외돼야 한다.
        self.assertTrue(context.was_truncated)  # 일부가 제한됐다는 표시가 참이어야 한다.


if __name__ == "__main__":  # 이 테스트 파일을 직접 실행했는지 확인한다.
    unittest.main()  # 파일 안의 모든 테스트를 실행한다.
