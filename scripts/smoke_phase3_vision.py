"""
Phase 3 Step 0 — Multimodal smoke test.

Verifies the round-trip works for our actual stack:
    OpenRouter Responses API → Anthropic Sonnet 4.5 with input_image

If this returns a sensible vision-aware answer, the rest of Phase 3 can
proceed. If it fails, we fall back to metadata-only.

Builds a tiny synthetic image with PIL (a red rectangle labeled
'red shirt size M'), base64-encodes it, sends it to Sonnet with the
prompt 'What does this image show?', and prints the answer.
"""

import base64
import json
import os
import urllib.request
import urllib.error
from io import BytesIO

from PIL import Image, ImageDraw
from dotenv import load_dotenv


def build_test_image() -> bytes:
    """Build a small JPEG: red rectangle with white text labelling itself."""
    img = Image.new("RGB", (320, 240), color=(180, 30, 30))
    d = ImageDraw.Draw(img)
    # Default font is small; the model should still read it
    d.text((20, 100), "RED SHIRT — SIZE M", fill=(255, 255, 255))
    d.text((20, 140), "CHECK: vision works", fill=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


def call_openrouter_vision(image_bytes: bytes, model: str, api_key: str) -> dict:
    """POST a Responses API request with an input_image content block."""
    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:image/jpeg;base64,{b64}"

    body = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text",
                     "text": "What does this image show? Be specific about the text you see."},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
        "max_output_tokens": 200,
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/responses",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://anthropic.com/research",
            "X-Title": "Project Deal A1 Phase 3 smoke",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        return {"_error": True, "status": e.code, "body": body_text}


def extract_text(result: dict) -> str:
    """Pull the assistant text out of an OpenRouter Responses API response."""
    if result.get("_error"):
        return f"[ERROR {result.get('status')}] {result.get('body','')[:500]}"
    # The Responses API output is a list of items
    for item in result.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") in ("output_text", "text"):
                    t = block.get("text") or block.get("content") or ""
                    if t:
                        return t
    return f"[NO TEXT FOUND in response] keys={list(result.keys())}"


def main():
    load_dotenv("/Users/ashijain/Documents/projectdealpoc/.env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY missing in .env")

    image_bytes = build_test_image()
    print(f"image bytes: {len(image_bytes)} ({len(image_bytes)/1024:.1f} KB)")

    for model in ["anthropic/claude-sonnet-4-5", "anthropic/claude-haiku-4-5"]:
        print(f"\n=== model: {model} ===")
        result = call_openrouter_vision(image_bytes, model, api_key)
        usage = result.get("usage", {})
        text = extract_text(result)
        print(f"response text:\n  {text}")
        if usage:
            print(f"usage: input={usage.get('input_tokens')}, "
                  f"output={usage.get('output_tokens')}, "
                  f"total={usage.get('total_tokens')}")


if __name__ == "__main__":
    main()
