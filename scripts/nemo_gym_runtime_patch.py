"""
Runtime monkey-patch for NeMo Gym to accept service_tier='standard' from
Anthropic's Claude Opus 4.7 API responses.

Background:
  Opus 4.7 returns `service_tier: "standard"` in its API response.
  NeMo Gym's Pydantic schema for NeMoGymResponse inherits service_tier from
  openai's Response class, which restricts it to {auto, default, flex,
  scale, priority}. The "standard" value crashes validation with a 500.

  Sonnet 4.5 / Haiku / Gemini all return values inside the allowed set, so
  this only matters when running Opus 4.7 as focal.

This patch:
  Replaces NeMoGymResponse.service_tier with Optional[str] so any value
  passes validation. The original validation for Sonnet/Haiku/Gemini is
  unaffected (their values still parse correctly).

How it gets loaded:
  scripts/restart_ng_run.sh copies this file as a `sitecustomize.py` into
  the policy_model subserver's venv site-packages directory. Python's
  site.py auto-imports sitecustomize at venv startup, before any other
  user code runs. The patched class is then visible to the model-server
  process.

  This file lives in OUR project repo (version controlled, easy to update).
  NeMo Gym's source files are not modified.
"""

from typing import Optional


def apply_patch():
    try:
        from nemo_gym.openai_utils import NeMoGymResponse
        from pydantic.fields import FieldInfo

        # Build a permissive field that accepts any string
        permissive = FieldInfo(annotation=Optional[str], default=None)
        NeMoGymResponse.model_fields['service_tier'] = permissive
        NeMoGymResponse.model_rebuild(force=True)
        # Diagnostic so we can confirm in the ng_run log
        print("[nemo_gym_runtime_patch] applied: NeMoGymResponse.service_tier now accepts any str")
    except Exception as e:
        # Log but don't crash — non-Opus runs should still work even if the
        # patch fails to apply (their service_tier values are already valid).
        print(f"[nemo_gym_runtime_patch] WARNING: patch failed: {e!r}")


# Apply at import time so sitecustomize-style loaders pick it up automatically.
apply_patch()
