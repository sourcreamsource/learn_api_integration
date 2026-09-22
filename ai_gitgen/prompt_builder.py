"""Git 변경 맥락을 AI가 이해할 요청문으로 바꾼다."""  # 파일의 책임을 설명한다.

from ai_gitgen.models import GitContext  # Git 변경 맥락 데이터 구조를 가져온다.


SYSTEM_PROMPT = """당신은 Git 변경 내용을 정확하고 간결하게 설명하는 도우미입니다.
제공된 변경 내용에 없는 사실을 추측하지 마세요.
비밀값처럼 보이는 내용은 출력하지 마세요.
결과는 한국어로 작성하세요."""  # 모든 명령에 공통으로 적용할 안전 규칙을 정한다.


def _context_block(context: GitContext) -> str:  # 두 명령이 공유할 Git 정보 블록을 만든다.
    files = "\n".join(f"- {path}" for path in context.changed_files) or "- 표시할 수 있는 파일 없음"  # 변경 파일을 불릿 목록으로 만든다.
    diff = context.diff_text or "(보안 정책에 따라 전송할 diff 내용이 없음)"  # diff가 비었을 때 이유를 알 수 있게 표시한다.
    return f"""현재 브랜치: {context.branch}
변경 파일:
{files}

Git 상태 요약:
{context.status_text}

Git diff:
{diff}"""  # AI가 변경 범위를 이해할 공통 정보를 돌려준다.


def build_commit_prompt(context: GitContext) -> str:  # 커밋 메시지 생성 전용 요청문을 만든다.
    return f"""아래 Git 변경 사항으로 커밋 메시지를 작성하세요.

규칙:
- 첫 줄은 type(scope): subject 형식의 제목으로 작성하세요.
- type은 feat, fix, docs, style, refactor, test, chore, build, ci, perf, revert 중 하나를 사용하세요.
- 제목은 권장 50자, 절대 최대 72자입니다.
- 제목 다음에는 빈 줄을 넣으세요.
- 본문에는 핵심 변경 1~2개를 '- ' 불릿으로 작성하세요.
- 코드 블록, 설명 문장, 'Commit Message' 라벨은 넣지 마세요.

{_context_block(context)}"""  # 형식 규칙과 실제 Git 정보를 합쳐 돌려준다.


def build_pr_prompt(context: GitContext) -> str:  # PR(Pull Request) 초안 생성 전용 요청문을 만든다.
    return f"""아래 Git 변경 사항으로 PR 제목과 본문 초안을 작성하세요.

반드시 JSON(JavaScript Object Notation) 객체 하나만 출력하세요.
JSON 형식:
{{"title":"80자 이하 한 줄 제목","body":"## Why\\n- 변경 배경\\n\\n## What\\n- 핵심 변경\\n\\n## How to Test\\n- 테스트 방법"}}

규칙:
- title은 한 줄이며 최대 80자입니다.
- body에는 ## Why, ## What, ## How to Test 순서의 섹션이 필요합니다.
- 각 섹션에는 '- '로 시작하는 불릿이 최소 1개 필요합니다.
- 코드 블록이나 JSON 밖의 설명은 넣지 마세요.

{_context_block(context)}"""  # JSON 출력 규칙과 실제 Git 정보를 합쳐 돌려준다.
