import json
import os
import time
import urllib.error
import urllib.request

API_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_MODEL = "grok-3-mini"
RETRY_DELAYS = (5, 15, 45)


def api_key() -> str | None:
    """Return the Grok API key from the environment, if set."""
    return os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY")


def model_name() -> str:
    """Return the Grok model name from the environment or the default."""
    return os.environ.get("GROK_MODEL", DEFAULT_MODEL)


def ask_grok(system: str, prompt: str) -> str:
    """Send one chat request to Grok and return the reply text."""
    key = api_key()
    if not key:
        raise ValueError("GROK_API_KEY is not set")
    body = json.dumps({
        "model": model_name(),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt, delay in enumerate((*RETRY_DELAYS, None)):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.load(response)
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            if not retryable or delay is None:
                raise OSError(f"Grok HTTP {error.code}: {error.read()[:300]!r}") from error
        time.sleep(delay)
    raise OSError("Grok request failed")
