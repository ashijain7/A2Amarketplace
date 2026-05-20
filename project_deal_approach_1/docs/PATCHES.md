# Local Patches to Upstream Code

**Status: NO ACTIVE PATCHES** — all three original patches have been reverted.

## Why patches were removed

The original approach (2026-05-17) put images in tool responses, which required
patching NeMo Gym. This was fragile: any `git pull` on NeMo Gym would silently
break Phase 3.

## New approach (no patches needed)

Images are embedded in the **initial task prompt** instead of in tool responses.
The OpenAI Responses API has always supported multimodal content in the input
message — NeMo Gym never restricted that path.

`tasks/generate_tasks.py :: build_initial_user_message_multimodal()` now includes:
1. Photos of the focal's **own items** (what they are offering to trade).
2. Photos of **other agents' items** whose category matches any of the focal's
   want categories — filtered so only relevant listings get images, keeping
   the context lean (typically 3–8 images, not 20+).

Everything else (tool responses, `_state_snapshot()`) remains plain JSON strings.

No NeMo Gym source files are modified.
