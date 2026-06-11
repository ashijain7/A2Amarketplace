# Razorpay MCP — test folder

Everything for testing Razorpay through its official MCP server lives here. The goal
of this first step is small: **prove the MCP server works with your keys, and find out
which payment abilities your test account actually has** — before we design anything.

Nothing here ever moves real money. It's all Razorpay **test mode** (fake money).

## What's in this folder

| File | What it is |
|---|---|
| `test_razorpay_mcp.py` | The probe script you run in the terminal. Connects to the Razorpay MCP server and prints a PASS/FAIL report. |
| `.env` | Your two TEST keys go here. Gitignored — never committed. |
| `.env.example` | A blank template for the keys. |
| `mcp_config.json` | Reference copy of how Claude Code is wired to the same MCP server. |
| `README.md` | This file. |

## Your part (about 5 minutes, on razorpay.com)

1. **Create a free account** at razorpay.com. No business, KYC, or documents needed for test mode.
2. **Switch to Test Mode** using the toggle in the dashboard.
3. **Generate test keys:** Settings → API Keys → *Generate Test Key*. You get:
   - a **Key ID** like `rzp_test_xxxxxxxx`
   - a **Key Secret** — shown only once, so copy it right away.
4. **Paste both** into `razorpay_mcp/.env` (replace the placeholder lines).

## Run the terminal test

From the project root:

```bash
uv run --script razorpay_mcp/test_razorpay_mcp.py
```

`uv` pulls in the small `mcp` library on its own — you don't install anything.
The first run also downloads the Razorpay MCP server (a Docker image), which can take
a minute. After that you'll see a PASS/FAIL report. Copy it back into the chat.

## Using it from Claude Code (already wired)

The same MCP server is registered with Claude Code under the name **razorpay**, so
Claude can call Razorpay's tools directly too. It reads your keys from `.env`, the same
as the script. After you fill in `.env`, reconnect it inside Claude Code with:

```
/mcp
```

To remove the wiring later: `claude mcp remove razorpay`.

## What the probe checks

- MCP server reachable + how many tools it offers
- Your keys authenticate (a harmless read)
- The agent can create a ₹500 order (a write)
- Whether payouts ("push money" to a seller) are available
- Whether the autonomous-pay tool `initiate_payment` is offered

The results tell us which payment rail to build the real agent-to-agent flow on.
