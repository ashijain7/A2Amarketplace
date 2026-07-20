"""Accept any `service_tier` string in a model response.

Claude Opus 4.7 returns `service_tier: "standard"`. NeMoGymResponse inherits the field
from openai's Response class, which restricts it to {auto, default, flex, scale,
priority}, so "standard" fails validation with a 500. Sonnet / Haiku / Gemini all return
values inside the allowed set.

This only WIDENS the field, so it is safe to leave installed for every focal model — the
allowed values still parse exactly as before, and a future model returning some other
string is covered too.
"""

from typing import Optional


def apply_patch():
    from nemo_gym.openai_utils import NeMoGymResponse
    from pydantic.fields import FieldInfo

    NeMoGymResponse.model_fields["service_tier"] = FieldInfo(
        annotation=Optional[str], default=None
    )
    NeMoGymResponse.model_rebuild(force=True)
