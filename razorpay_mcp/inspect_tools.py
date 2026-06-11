# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.2",
#     "python-dotenv>=1.0",
# ]
# ///
"""
Ask the Razorpay MCP server exactly what its payment tools need.

Prints, for each payment-related tool: its description, which fields are
REQUIRED, and all of its fields. This removes all guesswork before we write
the real "test every payment method" script.

Run from the project root:
    uv run --script razorpay_mcp/inspect_tools.py
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
DOCKER_IMAGE = "razorpay/mcp"

# The tools that matter for paying through the "collect" flow.
TOOLS_OF_INTEREST = [
    "create_order",
    "initiate_payment",
    "submit_otp",
    "resend_otp",
    "capture_payment",
    "fetch_payment",
    "create_payment_link",
    "payment_link_upi_create",
    "create_qr_code",
]


def load_keys():
    load_dotenv(HERE / ".env")
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id or not key_secret:
        sys.exit("No keys in razorpay_mcp/.env")
    docker = shutil.which("docker")
    if not docker:
        sys.exit("docker not found on PATH")
    return docker, key_id, key_secret


def describe(tool):
    print(f"\n{'=' * 64}\n{tool.name}\n{'=' * 64}")
    print((tool.description or "(no description)").strip())
    schema = tool.inputSchema or {}
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    if not props:
        print("  (no input fields)")
        return
    print("\nfields (★ = required):")
    for field, spec in props.items():
        star = "★" if field in required else " "
        ftype = spec.get("type", "?")
        desc = (spec.get("description", "") or "").strip().replace("\n", " ")
        if len(desc) > 90:
            desc = desc[:90] + "..."
        # show nested object fields one level deep (cards/upi live here)
        nested = ""
        if ftype == "object" and isinstance(spec.get("properties"), dict):
            nested = "  {" + ", ".join(spec["properties"].keys()) + "}"
        print(f"  {star} {field} ({ftype}){nested}: {desc}")


async def main():
    docker, key_id, key_secret = load_keys()
    server = StdioServerParameters(
        command=docker,
        args=["run", "--rm", "-i",
              "-e", f"RAZORPAY_KEY_ID={key_id}",
              "-e", f"RAZORPAY_KEY_SECRET={key_secret}",
              DOCKER_IMAGE],
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name: t for t in (await session.list_tools()).tools}
            for name in TOOLS_OF_INTEREST:
                if name in tools:
                    describe(tools[name])
                else:
                    print(f"\n{'=' * 64}\n{name}\n{'=' * 64}\n  NOT OFFERED by this server")


if __name__ == "__main__":
    asyncio.run(main())
