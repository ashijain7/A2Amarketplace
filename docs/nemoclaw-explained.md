# NemoClaw — Complete Reference

**Date:** 2026-05-15
**Status:** Research notes, not yet integrated into project

---

## 1. What NemoClaw Is (One Line)

A secure deployment stack for running a personal AI assistant that lives on your machine 24/7, connects to your messaging apps, and takes actions autonomously — with full sandboxing so it can't do anything you haven't approved.

---

## 2. The Three-Layer Stack

NemoClaw bundles three separate pieces together:

```
┌─────────────────────────────────────────────────────────┐
│                      NEMOCLAW                           │
│              (installer + orchestrator)                 │
│                                                         │
│   ┌────────────────┐      ┌────────────────────────┐   │
│   │   OPENCLAW     │      │      OPENSHELL         │   │
│   │                │      │                        │   │
│   │  The agent     │      │  The security runtime  │   │
│   │  framework     │      │  (sandbox container)   │   │
│   │                │      │                        │   │
│   │  - Memory      │      │  - Isolates the agent  │   │
│   │  - Tools       │      │  - Blocks network by   │   │
│   │  - Always-on   │      │    default             │   │
│   │  - Messaging   │      │  - API keys never      │   │
│   │    channels    │      │    enter sandbox       │   │
│   └────────────────┘      └────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Each Piece Explained

### 3.1 OpenClaw — The Agent

OpenClaw is an open-source AI assistant framework. It runs locally and persistently — not as a chatbot you ping, but as a daemon running in the background.

**The key idea: heartbeat model, not request-response**

```
Traditional chatbot (ChatGPT):
  You type → AI replies → done.
  It waits for you. Does nothing without you.

OpenClaw:
  Every N minutes the agent wakes up
  → checks its task list
  → acts if anything needs doing
  → goes back to sleep
  No human required.
```

**What it can do:**

| Capability | Detail |
|---|---|
| Messaging channels | Telegram, Slack, Discord, WhatsApp, Signal, Teams, Matrix, IRC, and more |
| Persistent memory | Remembers your conversations, habits, preferences across sessions |
| Tool use | Web search, file management, code execution, API calls |
| Multi-step autonomy | "Research X and send me a summary" — it does it while you sleep |
| Scheduling | Runs tasks on a timer or trigger without you initiating them |

---

### 3.2 OpenShell — The Security Container

The problem with autonomous agents: they can do anything — including things you didn't want, like leaking your API keys or hitting unexpected endpoints.

OpenShell solves this by intercepting everything the agent tries to do:

```
Agent inside sandbox wants to call api.openai.com
                    │
                    ▼
         ┌──────────────────────┐
         │   OPENSHELL          │
         │   GATEWAY (L7 proxy) │  ← intercepts ALL outbound calls
         └──────────────────────┘
                    │
    Shows you in real time:
    "Agent wants to connect to api.openai.com:443"
                [APPROVE]  [DENY]
```

**Critical security property: your API keys never enter the sandbox.**

The agent calls `inference.local`. OpenShell holds your actual API key on the host and rewrites the request as it passes through the gateway. The agent never sees your credential.

**Security layers used:**
- **Landlock** — filesystem isolation (agent can't read your files unless allowed)
- **seccomp** — syscall filtering (limits what system calls the agent process can make)
- **Network namespace isolation** — agent has its own network stack, all egress goes through OpenShell gateway

---

### 3.3 NemoClaw — The Orchestrator

NemoClaw is the layer that sets all of this up, wires it together, and manages its lifecycle. It adds on top of OpenClaw + OpenShell:

- **Guided onboarding wizard** — one command to configure everything
- **Hardened blueprint** — a versioned, tested image that's known to work
- **State management** — persists config across restarts
- **Inference routing** (experimental) — a LiteLLM proxy that automatically picks the cheapest/most appropriate model for each query using an LLM Router v3 engine
- **Lifecycle management** — start, stop, update, rebuild sandboxes cleanly

---

## 4. Setup — Step by Step

### 4.1 Prerequisites

| Requirement | Detail |
|---|---|
| CPU | 4+ vCPU minimum |
| RAM | 8 GB minimum, 16 GB recommended |
| Disk | 20 GB free (sandbox image is ~2.4 GB compressed) |
| Node.js | 22.16.0+ |
| npm | 10+ |
| Docker | Running instance required |
| OS | Linux (primary), macOS (Docker Desktop or Colima), Windows WSL2 |

> Note: NemoClaw is alpha software as of March 2026. APIs and behavior may change without notice. Not production-ready.

---

### 4.2 Installation

One command installs everything:

```bash
curl -fsSL https://install.nemoclaw.io | bash
```

What this does automatically:
1. Clones the NemoClaw repository
2. Validates Node.js version compatibility
3. Installs Docker dependencies
4. Sets up **OpenShell CLI v0.0.39** (this exact version is required — credential rewriting for REST and WebSocket depends on it)
5. Builds the NemoClaw CLI

**Verify the install:**
```bash
nemoclaw --version
openshell --version   # must show 0.0.39
```

**Manual install (for developers):**
```bash
# Step 1: Install Node.js 22
# Step 2: Ensure Docker is running
# Step 3: Build from source
npm run build:cli
```

**Uninstall:**
```bash
# Use the compatibility wrapper — cleans up NemoClaw while preserving system tools
nemoclaw uninstall
```

---

### 4.3 Onboarding Wizard

After installation, run:

```bash
nemoclaw onboard
```

The wizard walks through 6 steps:

**Step 1 — Inference Provider** (pick one):
```
1. NVIDIA Endpoints (build.nvidia.com)
2. OpenAI
3. Anthropic
4. Google Gemini
5. OpenAI-compatible endpoint   ← use this for OpenRouter
6. Local Ollama
7. Local vLLM
8. NVIDIA NIM
```

**Step 2 — Model**
Enter the model ID. For OpenRouter: `anthropic/claude-sonnet-4-5` or any model available on OpenRouter.

**Step 3 — API Key**
Your key is stored on the host only. It never enters the sandbox. OpenShell proxies it transparently.

**Step 4 — Sandbox Name**
Give your assistant a name, e.g. `my-assistant`.

**Step 5 — Optional Features**
- Brave Web Search integration (y/n)
- Messaging channel: Telegram / Slack / Discord / WhatsApp / Signal / Teams / etc.

**Step 6 — Network Policy**
```
Strict    — almost nothing allowed outbound by default
Balanced  — sensible defaults (recommended for most users)
Permissive — most things allowed, you review exceptions
```

Build time after wizard: **5–15 minutes** (downloads sandbox image).

> Note: If using a local Nemotron 120B model, add 15–30 minutes for the ~87 GB model download.

---

### 4.4 Running Your Assistant

**Browser dashboard:**
```
http://127.0.0.1:18789/
```

**Terminal (connect to sandbox):**
```bash
nemoclaw my-assistant connect
# inside the sandbox:
openclaw tui
```

**Send a one-off message:**
```bash
openclaw agent --agent main --local -m "hello" --session-id test
```

**Via messaging app:**
If you set up Telegram during onboarding, your agent is now live in your Telegram — just message it.

---

### 4.5 OpenRouter Configuration

During onboarding, pick option 5 (OpenAI-compatible endpoint) and enter:

```
Base URL:  https://openrouter.ai/api/v1
API key:   your_openrouter_key_here
Model:     anthropic/claude-sonnet-4-5
```

That's it. Your key stays on the host. The agent never sees it.

---

## 5. How It All Flows — One Complete Picture

```
You (via Telegram/Slack/Browser)
          │
          │ message: "research the latest on agent-to-agent markets"
          ▼
    ┌──────────────┐
    │   OPENCLAW   │  ← receives your message
    │   (agent)    │  ← decides: I need web search + time to think
    └──────────────┘
          │
          │ tries to call: brave.search.api:443
          ▼
    ┌──────────────────────────┐
    │   OPENSHELL GATEWAY      │  ← intercepts the call
    │                          │  ← checks: is brave.search in policy?
    │   [shows you the request]│  ← if Balanced policy: yes, allow
    └──────────────────────────┘
          │
          │ proxied call with your API key injected
          ▼
    External API (Brave Search, OpenRouter, etc.)
          │
          │ result back through gateway
          ▼
    ┌──────────────┐
    │   OPENCLAW   │  ← sees result, reasons over it
    │   (agent)    │  ← writes summary
    └──────────────┘
          │
          │ sends reply back to you via Telegram
          ▼
You receive: "Here's what I found on agent-to-agent markets..."
```

---

## 6. Command Reference

| Command | What it does |
|---|---|
| `nemoclaw onboard` | Run the setup wizard |
| `nemoclaw my-assistant connect` | Connect to a named sandbox |
| `nemoclaw --version` | Check NemoClaw version |
| `openshell --version` | Check OpenShell version |
| `openclaw tui` | Launch terminal UI inside sandbox |
| `openclaw agent --agent main --local -m "msg"` | Send one message to the agent |
| `/nemoclaw` | Slash commands inside the sandbox for config |

---

## 7. NemoClaw vs NeMo Gym — The Core Difference

These two NVIDIA tools are completely different. Easy to confuse because they both have "NeMo" in the name.

| | NeMo Gym | NemoClaw |
|---|---|---|
| **Purpose** | Evaluate and train LLM agents in simulated environments | Deploy a personal AI assistant securely |
| **Who uses it** | Researchers, ML engineers | Anyone who wants an always-on AI assistant |
| **What the agent does** | Solves tasks in a controlled environment, gets scored | Lives in your Telegram/Slack, helps you daily |
| **Always-on?** | No — runs rollouts on demand | Yes — heartbeat model, 24/7 |
| **Security focus** | None | Core — sandboxing, credential isolation, egress control |
| **Output** | Reward scores, JSONL rollout files | Real-world actions: messages sent, files changed, code run |
| **Inference** | Any OpenAI-compatible endpoint via env.yaml | Routed through OpenShell gateway |
| **Scale** | Thousands of concurrent rollouts | Single persistent agent per sandbox |

**Simple way to remember:**
- **NeMo Gym** = lab (you run experiments, measure results)
- **NemoClaw** = deployment (you run an assistant, it helps you live)

---

## 8. Relevance to This Project

### Not directly relevant to `project_deal_nemogym`

NemoClaw is designed for deploying a personal assistant, not for running marketplace simulations or comparing model performance. For `project_deal_nemogym`, NeMo Gym is the right tool.

### Where NemoClaw could be relevant later

If after studying Project Deal the goal shifts to building a **real** agent-to-agent system — not a simulation, but actual persistent agents representing actual people — NemoClaw is the deployment stack you'd reach for. Each persona would be a sandboxed OpenClaw instance, talking to others through messaging channels, with OpenShell ensuring no agent can do anything its "human" didn't approve.

That would be a much later project. For now, NeMo Gym handles the simulation and evaluation work.

---

## 9. Key Facts to Remember

- **Alpha software** (March 2026) — APIs will change, not for production
- **OpenShell v0.0.39** specifically required — pinned version
- **API keys stay on the host** — the sandbox never sees them
- **OpenRouter works** — pick "OpenAI-compatible endpoint" in the wizard
- **Heartbeat model** — agent acts autonomously on a timer, no human needed per action
- **Node.js 22.16+ required** — not Python-based (unlike NeMo Gym)
- **Docker required** — the sandbox is a container
