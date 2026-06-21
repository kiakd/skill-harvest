# tests/test_llm_client.py
import llm_client


def test_complete_posts_to_endpoint_and_returns_content():
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers

        class Resp:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "hello from llm"}}]}

            def raise_for_status(self):
                pass

        return Resp()

    out = llm_client.complete("say hi", poster=fake_post)
    assert out == "hello from llm"
    assert captured["url"].endswith("/chat/completions")
    assert captured["json"]["messages"][-1]["content"] == "say hi"
    assert "Authorization" in captured["headers"]
