# llm_client.py
"""Minimal OpenAI-compatible chat completion. `poster` injected for tests."""
import config


def _default_poster(url, json, headers, timeout):
    import requests
    return requests.post(url, json=json, headers=headers, timeout=timeout)


def complete(prompt, poster=None, timeout=120):
    """Send a single-user-message chat completion, return the content string."""
    poster = poster or _default_poster
    url = config.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    resp = poster(url, json=body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# Name used by summarize.py's lazy default import.
default_complete = complete
