# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.2",
#     "python-dotenv>=1.0",
# ]
# ///
"""
Razorpay MCP probe
==================
Checks that the official Razorpay MCP server works with YOUR test keys, and
reports which payment capabilities your account actually has.

Nothing here moves real money -- test mode only.

What it does, top to bottom:
  1. Reads your Razorpay TEST keys from razorpay_mcp/.env
  2. Starts the official Razorpay MCP server (via Docker) and connects to it
  3. Lists the tools the server exposes   -> proves MCP is working
  4. Reads your payments (a harmless read) -> proves your keys authenticate
  5. Creates a test Order for Rs 500       -> proves the agent can create/pay
  6. Peeks at payouts                       -> tells us if "push money" works

Run it from the project root:
    uv run --script razorpay_mcp/test_razorpay_mcp.py
"""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    sys.exit(
        "The 'mcp' library isn't available.\n"
        "Run this with uv so it gets pulled in automatically:\n"
        "    uv run --script razorpay_mcp/test_razorpay_mcp.py"
    )

HERE = Path(__file__).resolve().parent
DOCKER_IMAGE = "razorpay/mcp"
PROBE_AMOUNT_PAISE = 50_000  # Rs 500.00 (Razorpay counts in paise: 100 paise = Rs 1)


def banner(msg: str) -> None:
    print(f"\n{'=' * 62}\n{msg}\n{'=' * 62}")


def preflight():
    """Make sure keys and Docker are ready before we try to connect."""
    load_dotenv(HERE / ".env")
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

    if not key_id or not key_secret or "xxxx" in key_id or "your_test" in key_secret:
        sys.exit(
            "No Razorpay keys found.\n"
            f"Open {HERE / '.env'} and fill in your TEST keys:\n"
            "    RAZORPAY_KEY_ID=rzp_test_xxxxxxxx\n"
            "    RAZORPAY_KEY_SECRET=your_test_secret\n\n"
            "Get them at: Razorpay dashboard (switch to Test Mode)\n"
            "             -> Settings -> API Keys -> Generate Test Key"
        )
    if not key_id.startswith("rzp_test_"):
        print(f"!! Heads up: '{key_id[:12]}...' doesn't look like a TEST key (those start with rzp_test_).")

    docker = shutil.which("docker")
    if not docker:
        sys.exit("Docker isn't on your PATH. This script runs the Razorpay MCP server through Docker.")
    if subprocess.run([docker, "info"], capture_output=True).returncode != 0:
        sys.exit("Docker is installed but the engine isn't running.\nOpen Docker Desktop, wait until it's ready, then re-run.")

    print("Pulling the Razorpay MCP server image (first time only, can take a minute)...")
    pull = subprocess.run([docker, "pull", DOCKER_IMAGE], capture_output=True, text=True)
    if pull.returncode != 0:
        sys.exit(f"Couldn't pull {DOCKER_IMAGE}:\n{pull.stderr.strip()}")
    print("Image ready.")
    return docker, key_id, key_secret


def text_of(result) -> str:
    """Pull readable text out of an MCP tool result."""
    parts = [getattr(block, "text", "") for block in result.content]
    return " ".join(p for p in parts if p).strip() or "(no text returned)"


async def try_tool(session, name: str, args: dict, results: dict) -> None:
    """Call one tool, record pass/fail, print a short line."""
    try:
        res = await session.call_tool(name, args)
        if res.isError:
            results[name] = False
            print(f"  FAIL  {name}: {text_of(res)[:280]}")
        else:
            results[name] = True
            print(f"  PASS  {name}: {text_of(res).replace(chr(10), ' ')[:200]}")
    except Exception as e:
        results[name] = False
        print(f"  FAIL  {name}: {e}")


async def main() -> None:
    banner("STEP 1  -  checking your keys and Docker")
    docker, key_id, key_secret = preflight()
    print(f"Using test key {key_id[:14]}...")

    server = StdioServerParameters(
        command=docker,
        args=[
            "run", "--rm", "-i",
            "-e", f"RAZORPAY_KEY_ID={key_id}",
            "-e", f"RAZORPAY_KEY_SECRET={key_secret}",
            DOCKER_IMAGE,
        ],
    )

    results: dict = {}
    names: list = []
    has_initiate = False

    banner("STEP 2  -  connecting to the Razorpay MCP server")
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  PASS  MCP handshake succeeded -- the server is talking to us")

            banner("STEP 3  -  tools the MCP server offers")
            tools = (await session.list_tools()).tools
            names = sorted(t.name for t in tools)
            print(f"  PASS  {len(names)} tools available:")
            for n in names:
                print(f"          - {n}")
            has_initiate = "initiate_payment" in names

            banner("STEP 4  -  read test (do your keys authenticate?)")
            await try_tool(session, "fetch_all_payments", {"count": 1}, results)

            banner("STEP 5  -  write test (can the agent create a Rs 500 order?)")
            await try_tool(
                session, "create_order",
                {"amount": PROBE_AMOUNT_PAISE, "currency": "INR", "receipt": "mcp-probe-001"},
                results,
            )

            banner("STEP 6  -  is 'push money' (payouts) available?")
            await try_tool(session, "fetch_all_payouts", {"count": 1}, results)

    banner("SUMMARY  (copy this whole block back into the chat)")
    print(f"  PASS  MCP server reachable, {len(names)} tools exposed")
    print(f"  {'PASS' if results.get('fetch_all_payments') else 'FAIL'}  keys authenticate (read)")
    print(f"  {'PASS' if results.get('create_order') else 'FAIL'}  can create an order (write)")
    if results.get("fetch_all_payouts"):
        print("  PASS  payouts readable (RazorpayX looks enabled)")
    else:
        print("  ----  payouts not readable (RazorpayX probably not enabled -- normal on a fresh account)")
    if has_initiate:
        print("  PASS  autonomous-pay tool 'initiate_payment' is offered")
    else:
        print("  ----  'initiate_payment' not in the tool list")
    print("\nDone. Paste everything above back and we'll design the real flow on what passed.")


if __name__ == "__main__":
    asyncio.run(main())
