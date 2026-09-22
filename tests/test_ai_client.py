"""두 AI API 형식의 요청 생성과 응답 처리를 검사한다."""  # 테스트 파일의 책임을 설명한다.

import io  # 가짜 HTTP 오류 본문을 바이트 스트림으로 만든다.
import json  # 요청과 응답 JSON을 확인한다.
import unittest  # Python 기본 테스트 도구를 가져온다.
from unittest.mock import patch  # 실제 네트워크 대신 가짜 응답을 연결한다.
import urllib.error  # 가짜 HTTP 오류를 만든다.

from ai_gitgen.ai_client import generate_text  # 검사할 API 호출 함수를 가져온다.
from ai_gitgen.errors import ApiRequestError  # API 실패 오류를 확인하기 위해 가져온다.
from ai_gitgen.models import ApiSettings  # 테스트용 API 설정 객체를 만든다.


class FakeResponse:  # urlopen처럼 동작하는 최소 가짜 응답을 만든다.
    def __init__(self, payload: dict[str, object]) -> None:  # 응답 JSON을 받아 초기화한다.
        self.body = json.dumps(payload).encode("utf-8")  # Python 값을 UTF-8 JSON 바이트로 저장한다.

    def __enter__(self) -> "FakeResponse":  # with 문에 들어갈 때 자기 자신을 돌려준다.
        return self  # 실제 HTTP 응답처럼 사용할 객체를 제공한다.

    def __exit__(self, *args: object) -> None:  # with 문을 빠져나올 때 호출된다.
        return None  # 닫을 실제 네트워크 자원이 없으므로 아무 작업도 하지 않는다.

    def read(self) -> bytes:  # 실제 응답과 같은 read 메서드를 제공한다.
        return self.body  # 저장해 둔 JSON 바이트를 돌려준다.


def make_settings(api_format: str) -> ApiSettings:  # 반복 사용할 테스트 설정을 만든다.
    return ApiSettings("fake-key", "https://example.test/v1", api_format, "test-model", 0.2, 300, 5.0)  # 외부로 전송되지 않는 가짜 값만 사용한다.


class AiClientTest(unittest.TestCase):  # API 클라이언트 동작 검사를 묶는다.
    @patch("urllib.request.urlopen")  # 실제 네트워크 함수를 가짜 객체로 바꾼다.
    def test_openai_response_is_extracted(self, urlopen: object) -> None:  # OpenAI 응답 텍스트 추출을 검사한다.
        urlopen.return_value = FakeResponse({"choices": [{"message": {"content": "commit result"}}]})  # OpenAI 호환 가짜 응답을 준비한다.
        result = generate_text(make_settings("openai"), "system", "user")  # 가짜 응답으로 함수를 실행한다.
        self.assertEqual(result, "commit result")  # 생성 텍스트가 정확히 추출되어야 한다.
        self.assertEqual(urlopen.call_count, 1)  # API 호출은 정확히 한 번이어야 한다.
        request = urlopen.call_args.args[0]  # 함수에 전달된 HTTP 요청 객체를 꺼낸다.
        body = json.loads(request.data.decode("utf-8"))  # 요청 본문을 다시 Python 값으로 읽는다.
        self.assertEqual(body["temperature"], 0.2)  # temperature 옵션이 요청에 전달되어야 한다.
        self.assertEqual(body["max_tokens"], 300)  # max_tokens 옵션이 요청에 전달되어야 한다.
        self.assertEqual(request.get_header("Authorization"), "Bearer fake-key")  # OpenAI Bearer 인증 헤더가 있어야 한다.

    @patch("urllib.request.urlopen")  # 실제 네트워크 함수를 가짜 객체로 바꾼다.
    def test_anthropic_response_is_extracted(self, urlopen: object) -> None:  # Anthropic 응답 텍스트 추출을 검사한다.
        urlopen.return_value = FakeResponse({"content": [{"type": "text", "text": "part one"}, {"type": "text", "text": "part two"}]})  # Anthropic 가짜 응답을 준비한다.
        result = generate_text(make_settings("anthropic"), "system", "user")  # 가짜 응답으로 함수를 실행한다.
        self.assertEqual(result, "part one\npart two")  # 텍스트 블록이 순서대로 합쳐져야 한다.
        request = urlopen.call_args.args[0]  # 함수에 전달된 HTTP 요청 객체를 꺼낸다.
        self.assertEqual(request.get_header("X-api-key"), "fake-key")  # Anthropic x-api-key 인증 헤더가 있어야 한다.
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")  # Anthropic API 버전 헤더가 있어야 한다.

    @patch("urllib.request.urlopen")  # 실제 네트워크 함수를 가짜 오류로 바꾼다.
    def test_http_error_is_sanitized(self, urlopen: object) -> None:  # HTTP 오류에 비밀값이 남지 않는지 검사한다.
        body = io.BytesIO(b'{"error":{"message":"api_key=hidden-secret"}}')  # 가짜 비밀값이 든 오류 본문을 만든다.
        urlopen.side_effect = urllib.error.HTTPError("https://example.test", 401, "Unauthorized", {}, body)  # 401 인증 오류를 준비한다.
        with self.assertRaises(ApiRequestError) as caught:  # 안전한 API 오류가 발생해야 통과시킨다.
            generate_text(make_settings("openai"), "system", "user")  # 실패하는 API 호출을 실행한다.
        self.assertIn("HTTP 401", str(caught.exception))  # 사용자가 상태 코드는 확인할 수 있어야 한다.
        self.assertNotIn("hidden-secret", str(caught.exception))  # 비밀값 원문은 오류에 없어야 한다.

    @patch("urllib.request.urlopen")  # 실제 네트워크 함수를 잘못된 응답으로 바꾼다.
    def test_invalid_json_fails_cleanly(self, urlopen: object) -> None:  # JSON이 아닌 응답 처리를 검사한다.
        response = FakeResponse({"unused": True})  # 기본 가짜 응답 객체를 만든다.
        response.body = b"not-json"  # 응답 본문을 잘못된 JSON으로 바꾼다.
        urlopen.return_value = response  # 잘못된 응답을 반환하도록 설정한다.
        with self.assertRaises(ApiRequestError):  # 사용자용 API 오류가 발생해야 통과시킨다.
            generate_text(make_settings("openai"), "system", "user")  # 잘못된 JSON 응답을 처리한다.


if __name__ == "__main__":  # 이 테스트 파일을 직접 실행했는지 확인한다.
    unittest.main()  # 파일 안의 모든 테스트를 실행한다.
