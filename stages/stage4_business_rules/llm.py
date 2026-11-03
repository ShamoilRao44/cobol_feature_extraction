"""One OpenAI-compatible chat client. Switch provider by changing config values only.

Settings come from the .env file in the project root (optional), and real environment
variables override it:
  LLM_BASE_URL       e.g. https://api.x.ai/v1  or  http://localhost:8000/v1
  LLM_MODEL          e.g. grok-3-mini          or  the local Qwen model name
  LLM_API_KEY        empty is allowed for local servers that need no key
  LLM_CONTEXT_TOKENS max prompt + output tokens of the model (default 64000)
  LLM_MAX_OUTPUT_TOKENS tokens reserved for the reply (default 8000)
"""
import json
import os
import time
import urllib.error
import urllib.request

from dotenv import dotenv_values

ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env",
)
DEFAULTS = {
    "base_url": "https://api.x.ai/v1",
    "model": "grok-3-mini",
    "api_key": "",
    "context_tokens": 64000,
    "max_output_tokens": 8000,
}
ENV_NAMES = {
    "base_url": "LLM_BASE_URL",
    "model": "LLM_MODEL",
    "api_key": "LLM_API_KEY",
    "context_tokens": "LLM_CONTEXT_TOKENS",
    "max_output_tokens": "LLM_MAX_OUTPUT_TOKENS",
}
CHARS_PER_TOKEN = 3
RETRY_DELAYS = (5, 15, 45)


def load_config() -> dict:
    """Return LLM settings: defaults, then the .env file, then environment variables."""
    config = dict(DEFAULTS)
    file_values = dotenv_values(ENV_PATH) if os.path.isfile(ENV_PATH) else {}
    for key, env_name in ENV_NAMES.items():
        value = os.environ.get(env_name) or file_values.get(env_name)
        if value:
            config[key] = value
    config["base_url"] = str(config["base_url"]).rstrip("/")
    config["context_tokens"] = int(config["context_tokens"])
    config["max_output_tokens"] = int(config["max_output_tokens"])
    return config


def config_error(config: dict) -> str | None:
    """Return a message when the settings cannot work, else None."""
    if not config["base_url"] or not config["model"]:
        return "LLM_BASE_URL and LLM_MODEL must be set (in .env or the environment)"
    if "api.x.ai" in config["base_url"] and not config["api_key"]:
        return "LLM_API_KEY is not set (required for the Grok API)"
    if config["max_output_tokens"] >= config["context_tokens"]:
        return "max_output_tokens must be smaller than context_tokens"
    return None


def estimate_tokens(text: str) -> int:
    """Estimate tokens conservatively (code is dense, so ~3 characters per token)."""
    return len(text) // CHARS_PER_TOKEN + 1


def prompt_budget(config: dict) -> int:
    """Return how many tokens a prompt may use while leaving room for the reply."""
    return config["context_tokens"] - config["max_output_tokens"]


def ask_llm(system: str, prompt: str, config: dict | None = None) -> str:
    """Send one chat completion request and return the reply text."""
    config = config or load_config()
    error = config_error(config)
    if error:
        raise ValueError(error)
    needed = estimate_tokens(system) + estimate_tokens(prompt)
    if needed > prompt_budget(config):
        raise ValueError(f"prompt needs ~{needed} tokens, budget is {prompt_budget(config)}")
    body = json.dumps({
        "model": config["model"],
        "temperature": 0,
        "max_tokens": config["max_output_tokens"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"
    request = urllib.request.Request(
        f"{config['base_url']}/chat/completions", data=body, headers=headers, method="POST"
    )
    for delay in (*RETRY_DELAYS, None):
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                data = json.load(response)
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            if not retryable or delay is None:
                raise OSError(f"LLM HTTP {error.code}: {error.read()[:300]!r}") from error
        time.sleep(delay)
    raise OSError("LLM request failed")
