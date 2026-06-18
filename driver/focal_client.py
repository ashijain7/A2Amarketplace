"""Direct OpenRouter Responses-API call for the focal — the driver's replacement
for NeMo Gym's policy server. Mirrors marketplace/llm.py: OpenAI SDK pointed at
OpenRouter, with a real timeout + retry (the missing timeout was the hang)."""
import os, time
from openai import OpenAI, APITimeoutError, APIConnectionError, APIStatusError

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

RETRY_STATUS = {429, 500, 502, 503, 504, 520}

def call_focal(model, input_items, tools, *, timeout=120.0, max_retries=3):
    last = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = _client.responses.create(
                model=model, input=input_items, tools=tools, timeout=timeout,
            )
            return resp.model_dump()
        except (APITimeoutError, APIConnectionError) as e:
            last = e
            print(f"[focal_client] {type(e).__name__} try {attempt}/{max_retries}; retrying", flush=True)
            time.sleep(1.0)
        except APIStatusError as e:
            if e.status_code in RETRY_STATUS and attempt < max_retries:
                last = e
                print(f"[focal_client] HTTP {e.status_code} try {attempt}/{max_retries}; retrying", flush=True)
                time.sleep(1.0)
            else:
                raise
    raise last
