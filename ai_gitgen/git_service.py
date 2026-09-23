"""Git 명령을 실행하고 AI에 전달할 변경 맥락을 수집한다."""  # 파일의 책임을 설명한다.

from pathlib import Path  # 현재 경로와 저장소 루트를 안전하게 비교한다.
import subprocess  # Python에서 Git 명령을 직접 실행한다.

from ai_gitgen.errors import GitRepositoryError  # Git 관련 사용자 오류를 가져온다.
from ai_gitgen.models import GitContext  # 수집 결과 데이터 구조를 가져온다.
from ai_gitgen.security import SAFE_MAX_FILES, is_protected_path, limit_diff_lines, mask_sensitive_text  # 보안 처리 도구를 가져온다.


def _run_git(arguments: list[str], accepted_codes: tuple[int, ...] = (0,)) -> str:  # Git 명령을 한 방식으로 실행한다.
    completed = subprocess.run(  # 명령 실행 결과를 변수에 저장한다.
        ["git", *arguments],  # 셸을 통하지 않고 Git과 인자를 분리해 전달한다.
        capture_output=True,  # 표준 출력과 오류를 터미널에 노출하지 않고 모은다.
        text=True,  # 바이트가 아니라 문자열로 결과를 받는다.
        encoding="utf-8",  # Git 출력을 UTF-8(Unicode Transformation Format 8-bit)로 읽는다.
        errors="replace",  # 잘못된 문자가 있어도 프로그램 전체가 멈추지 않게 바꿔 읽는다.
        check=False,  # 반환 번호를 아래에서 직접 검사한다.
    )  # Git 명령 실행을 마친다.
    if completed.returncode not in accepted_codes:  # 예상하지 못한 실패 번호인지 확인한다.
        detail = mask_sensitive_text(completed.stderr.strip())[:300]  # 오류문에서도 민감정보를 가리고 길이를 제한한다.
        raise GitRepositoryError(f"Git 명령 실행 실패: {detail or '원인을 확인할 수 없습니다.'}")  # 사용자가 이해할 오류로 바꾼다.
    return completed.stdout  # 성공한 Git 명령의 표준 출력을 돌려준다.


def _null_separated_paths(arguments: list[str]) -> list[str]:  # NUL(Null) 문자로 나뉜 Git 경로를 읽는다.
    output = _run_git(arguments)  # 요청받은 Git 명령을 실행한다.
    return [path for path in output.split("\0") if path]  # 빈 값은 버리고 실제 경로만 돌려준다.


def _has_head_commit() -> bool:  # 첫 커밋이 존재하는 저장소인지 확인한다.
    completed = subprocess.run(  # HEAD 존재 확인 명령을 실행한다.
        ["git", "rev-parse", "--verify", "HEAD"],  # 현재 커밋을 조용히 확인한다.
        capture_output=True,  # 확인 결과를 터미널에 노출하지 않는다.
        text=True,  # 결과를 문자열로 받는다.
        check=False,  # 커밋이 없는 반환 번호 128도 직접 처리한다.
    )  # HEAD 확인 명령을 마친다.
    return completed.returncode == 0  # 반환 번호가 0이면 커밋이 있다고 판단한다.


def _unique_paths(paths: list[str]) -> list[str]:  # 경로 순서를 유지하면서 중복을 제거한다.
    seen: set[str] = set()  # 이미 본 경로를 빠르게 찾기 위한 집합을 만든다.
    result: list[str] = []  # 중복 없는 최종 경로를 담을 목록을 만든다.
    for path in paths:  # 입력 경로를 앞에서부터 하나씩 확인한다.
        if path not in seen:  # 아직 처리하지 않은 경로인지 확인한다.
            seen.add(path)  # 다음 중복을 막기 위해 본 경로로 기록한다.
            result.append(path)  # 원래 순서를 유지하며 결과에 추가한다.
    return result  # 중복을 제거한 경로 목록을 돌려준다.


def _parse_status_codes(status_output: str) -> dict[str, str]:  # NUL 문자 형식의 Git 상태에서 파일별 상태 코드를 읽는다.
    records = status_output.split("\0")  # 파일 이름 안의 공백과 특수문자를 안전하게 구분한다.
    result: dict[str, str] = {}  # 경로와 두 글자 상태 코드를 연결할 사전을 만든다.
    index = 0  # 현재 읽을 레코드 위치를 0부터 시작한다.
    while index < len(records):  # 모든 상태 레코드를 처리할 때까지 반복한다.
        record = records[index]  # 현재 상태 레코드를 꺼낸다.
        if not record:  # 마지막 NUL 문자 뒤의 빈 레코드인지 확인한다.
            index += 1  # 다음 위치로 이동한다.
            continue  # 빈 값은 더 처리하지 않는다.
        code = record[:2]  # 앞의 두 글자 XY 상태 코드를 읽는다.
        path = record[3:]  # 상태 코드와 공백 뒤의 파일 경로를 읽는다.
        result[path] = code  # 선택 파일의 상태를 나중에 찾을 수 있게 저장한다.
        index += 2 if "R" in code or "C" in code else 1  # Rename 또는 Copy는 뒤의 원본 경로 레코드까지 건너뛴다.
    return result  # 파일별 실제 Git 상태 코드를 돌려준다.


def _collect_changed_paths(has_head: bool) -> tuple[list[str], set[str]]:  # 추적 파일과 새 파일 목록을 모은다.
    tracked_arguments = ["diff", "--name-only", "-z", "HEAD", "--"] if has_head else ["diff", "--cached", "--name-only", "-z", "--"]  # 저장소 상태에 맞는 추적 파일 명령을 고른다.
    tracked = _null_separated_paths(tracked_arguments)  # 커밋 기준으로 바뀐 추적 파일을 읽는다.
    if not has_head:  # 첫 커밋 전에는 작업 트리 변경도 따로 확인한다.
        tracked.extend(_null_separated_paths(["diff", "--name-only", "-z", "--"]))  # 스테이징되지 않은 추적 파일도 합친다.
    untracked = _null_separated_paths(["ls-files", "--others", "--exclude-standard", "-z"])  # Git이 아직 추적하지 않는 파일을 읽는다.
    return _unique_paths([*tracked, *untracked]), set(untracked)  # 전체 경로와 새 파일 집합을 돌려준다.


def _diff_for_path(path: str, has_head: bool, is_untracked: bool) -> str:  # 파일 하나의 diff를 만든다.
    if is_untracked:  # Git이 아직 추적하지 않는 새 파일인지 확인한다.
        return _run_git(["diff", "--no-index", "--no-ext-diff", "--unified=3", "--", "/dev/null", path], accepted_codes=(0, 1))  # 빈 파일과 비교해 새 파일 diff를 만든다.
    if has_head:  # 비교할 HEAD 커밋이 있는지 확인한다.
        return _run_git(["diff", "--no-ext-diff", "--unified=3", "HEAD", "--", path])  # 스테이징 여부와 관계없이 HEAD와 비교한다.
    staged = _run_git(["diff", "--cached", "--no-ext-diff", "--unified=3", "--", path])  # 첫 커밋 전 스테이징 변경을 읽는다.
    unstaged = _run_git(["diff", "--no-ext-diff", "--unified=3", "--", path])  # 첫 커밋 전 작업 트리 변경을 읽는다.
    return "\n".join(part for part in (staged, unstaged) if part)  # 두 변경 내용을 빈 부분 없이 합친다.


# ------------------------------------------------------------------------------------------
# 🔥🔥🔥🔥🔥 핵심 함수
def collect_git_context(safe_mode: bool = True) -> GitContext:  # 현재 저장소의 변경 맥락을 모은다.
    try:  # Git 저장소 확인 실패를 이해하기 쉬운 오류로 바꾸기 시작한다.
        root_text = _run_git(["rev-parse", "--show-toplevel"]).strip()  # Git 저장소 최상위 경로를 찾는다.

    except GitRepositoryError as error:  # Git 저장소가 아닐 때 발생한 오류를 잡는다.
        raise GitRepositoryError("현재 폴더는 Git 저장소가 아닙니다. 프로젝트 루트에서 실행하세요.") from error  # 해결 방법이 담긴 오류로 바꾼다.


    if Path.cwd().resolve() != Path(root_text).resolve():  # 사용자가 저장소 하위 폴더에서 실행했는지 확인한다.
        raise GitRepositoryError("Git 저장소의 루트 폴더에서 실행하세요.")  # 요구사항에 맞는 실행 위치를 안내한다.

    status_raw = _run_git(["status", "--porcelain=v1", "--untracked-files=all", "-z"])  # 특수문자 경로도 안전한 기계 판독용 Git 상태를 수집한다.

    if not status_raw.strip():  # 상태 출력이 비어 변경 사항이 없는지 확인한다.
        return GitContext("", (), "", "", 0, 0, (), False)  # API를 부르지 않도록 빈 변경 맥락을 돌려준다.

    has_head = _has_head_commit()  # 첫 커밋이 존재하는지 확인한다.

    changed_paths, untracked_paths = _collect_changed_paths(has_head)  # 실제 변경 경로를 모은다.

    protected = [path for path in changed_paths if is_protected_path(path)]  # 비밀 파일 경로를 먼저 분리한다.

    allowed = [path for path in changed_paths if path not in protected]  # 비밀 파일을 전송 후보에서 제거한다.

    selected = allowed[:SAFE_MAX_FILES] if safe_mode else allowed  # 안전 모드에서는 최대 10개 파일만 고른다.

    limited = allowed[len(selected):]  # 파일 개수 제한으로 빠진 경로를 기록한다.

    diff_parts = [_diff_for_path(path, has_head, path in untracked_paths) for path in selected]  # 선택한 각 파일의 diff를 모은다.

    combined_diff = "\n".join(part.rstrip() for part in diff_parts if part.strip())  # 빈 diff를 빼고 하나의 텍스트로 합친다.

    was_truncated = bool(limited)  # 파일 제한이 적용됐으면 잘림 상태로 시작한다.

    if safe_mode:  # 기본 안전 모드에서 내용 마스킹과 줄 제한을 적용한다.
        combined_diff = mask_sensitive_text(combined_diff)  # 알려진 API Key, 토큰, 이메일, 비밀번호를 가린다.
        combined_diff, line_truncated = limit_diff_lines(combined_diff)  # 최대 200줄까지만 남긴다.
        was_truncated = was_truncated or line_truncated  # 파일 또는 줄 중 하나라도 잘렸는지 기록한다.

    branch = _run_git(["branch", "--show-current"]).strip() or "(detached HEAD)"  # 현재 브랜치 이름을 읽는다.

    status_codes = _parse_status_codes(status_raw)  # 수집한 Git 상태를 파일별 코드로 바꾼다.

    status_text = "\n".join(f"{status_codes.get(path, 'M ')} {path}" for path in selected)  # 허용된 파일만 실제 상태 코드와 함께 요약한다.

    excluded = tuple([*protected, *limited])  # 보안과 개수 제한으로 제외한 경로를 하나로 묶는다.

    return GitContext(branch, tuple(selected), status_text, combined_diff, len(combined_diff.splitlines()), len(changed_paths), excluded, was_truncated)  # 모든 수집 결과를 돌려준다.
