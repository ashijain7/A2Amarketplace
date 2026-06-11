# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.2",
#     "python-dotenv>=1.0",
# ]
# ///
"""
Prove ONE fully-autonomous UPI payment, no human in the loop.

Flow (all by the agent, zero clicks):
    create_order  ->  initiate_payment (vpa=success@razorpay)  ->  fetch_payment

This is the real "buyer-agent pays seller-agent" mechanism. In test mode the
handle `success@razorpay` auto-approves, so no phone / PIN / OTP is needed.

Run from the project root:
    uv run --script razorpay_mcp/test_pay_upi.py
"""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
DOCKER_IMAGE = "razorpay/mcp"
AMOUNT = 50_000          # Rs 500 in paise
PAYER_VPA = "success@razorpay"   # test handle that auto-succeeds


def keys():
    load_dotenv(HERE / ".env")
    kid = os.getenv("RAZORPAY_KEY_ID", "").strip()
    ksec = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not kid or not ksec:
        sys.exit("No keys in razorpay_mcp/.env")
    docker = shutil.which("docker")
    if not docker:
        sys.exit("docker not on PATH")
    return docker, kid, ksec


def text_of(result):
    return " ".join(getattr(b, "text", "") for b in result.content).strip()


async def call(session, name, args, *, show=900):
    res = await session.call_tool(name, args)
    raw = text_of(res)
    print(f"\n--- {name} ---")
    print(raw[:show] + ("…" if len(raw) > show else ""))
    if res.isError:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def find_payment_id(obj):
    """The payment id can show up under a few different keys."""
    if not isinstance(obj, dict):
        return None
    for k in ("razorpay_payment_id", "payment_id", "id"):
        v = obj.get(k)
        if isinstance(v, str) and v.startswith("pay_"):
            return v
    return None


async def main():
    docker, kid, ksec = keys()
    server = StdioServerParameters(
        command=docker,
        args=["run", "--rm", "-i",
              "-e", f"RAZORPAY_KEY_ID={kid}",
              "-e", f"RAZORPAY_KEY_SECRET={ksec}",
              DOCKER_IMAGE],
    )

    print(f"Paying Rs {AMOUNT // 100} from a UPI handle ({PAYER_VPA}) — fully automatic, no human.\n")

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("STEP 1  create the bill (order)")
            order = await call(session, "create_order",
                               {"amount": AMOUNT, "currency": "INR", "receipt": "upi-auto-001"})
            oid = order.get("id") if order else None
            if not oid:
                sys.exit("Could not create an order — stopping.")
            print(f"  -> order: {oid}")

            print("\nSTEP 2  the agent pays the bill over UPI (no human)")
            pay = await call(session, "initiate_payment",
                             {"amount": AMOUNT, "order_id": oid, "vpa": PAYER_VPA,
                              "email": "maya@example.com", "contact": "9999999999"})
            pid = find_payment_id(pay)
            print(f"  -> payment id: {pid or '(not found — see raw response above)'}")

            print("\nSTEP 3  confirm it actually went through")
            final_status = None
            if pid:
                for attempt in range(6):
                    await asyncio.sleep(2)
                    info = await call(session, "fetch_payment", {"payment_id": pid}, show=300)
                    final_status = info.get("status") if info else None
                    print(f"  -> attempt {attempt + 1}: status = {final_status}")
                    if final_status == "authorized":
                        print("     capturing the authorized payment...")
                        await call(session, "capture_payment",
                                   {"payment_id": pid, "amount": AMOUNT, "currency": "INR"}, show=300)
                    if final_status in ("captured", "failed"):
                        break

            print("\n" + "=" * 60)
            if final_status == "captured":
                print("RESULT:  ✅ UPI payment completed end-to-end, no human. Money 'landed'.")
            elif final_status == "authorized":
                print("RESULT:  ◑ payment authorized but not captured — close, needs a capture step.")
            elif final_status:
                print(f"RESULT:  status ended at '{final_status}' — see responses above.")
            else:
                print("RESULT:  couldn't confirm — the raw responses above tell us what to adjust.")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
