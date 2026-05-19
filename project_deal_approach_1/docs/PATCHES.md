# Local Patches to Upstream Code

This file tracks **local edits to upstream NeMo Gym source** that don't live
in this project. If you `git pull` NeMo Gym, re-apply these patches before
running Phase 3 multimodal experiments.

The patches enable the marketplace to return **multimodal tool responses**
(text + `input_image` content blocks) so the focal agent SEES actual photos
of other agents' listings during a rollout — not just text references.

Without these patches:
- The OpenAI Responses API itself supports multimodal tool outputs
  (`function_call_output.output: Union[str, ResponseFunctionCallOutputItemListParam]`)
- NeMo Gym intentionally narrowed this to `str` for simplicity
- `simple_agent` reads the marketplace's HTTP response with `.decode()` →
  always a string, never a structured content list

So we need patches at two upstream sites and one local-marketplace site.

---

## Patch 1 — `nemo_gym/openai_utils.py`

**Location:** `/Users/ashijain/Documents/nemo_gym_lib/nemo_gym/openai_utils.py`

**Imports section** (around line 70):

```python
from openai.types.responses.response_input_param import (
    ResponseFunctionCallOutputItemListParam,  # [LOCAL PATCH 2026-05-17] enables multimodal tool outputs
    ResponseInputMessageContentListParam,
)
```

**`NeMoGymFunctionCallOutput` class** (around line 173): widen `output` field
from `str` to `Union[str, ResponseFunctionCallOutputItemListParam]`.

```python
class NeMoGymFunctionCallOutput(BaseModel):
    """
    ... (existing docstring) ...

    [LOCAL PATCH 2026-05-17 — projectdealpoc Phase 3]
    Upstream NeMo Gym narrowed `output` to `str`. The upstream OpenAI Responses
    API spec actually allows `output: Union[str, ResponseFunctionCallOutputItemListParam]`
    so a tool can return multimodal content blocks (text + image + file). We widen
    the field to match the spec so the marketplace can return image content blocks
    inside tool responses (e.g., showing the focal photos of other agents' listings).
    """

    call_id: str
    # [LOCAL PATCH] widened from `str` to allow multimodal content lists.
    output: Union[str, ResponseFunctionCallOutputItemListParam]
    type: Literal["function_call_output"] = "function_call_output"
    id: Optional[str] = None
    status: Optional[Literal["in_progress", "completed", "incomplete"]] = None
```

---

## Patch 2 — `responses_api_agents/simple_agent/app.py`

**Location:** `/Users/ashijain/Documents/nemo_gym_lib/responses_api_agents/simple_agent/app.py`

In the tool-call loop, after `await self.server_client.post(...)`, detect
when the resources-server response is a JSON list of content blocks and
pass it through as a list instead of a string.

```python
# [LOCAL PATCH 2026-05-17 — projectdealpoc Phase 3]
# Detect multimodal tool outputs: if the resources server
# returned a JSON list of content blocks (input_text/input_image/
# input_file), pass the list through unchanged so the model
# receives real image content. Otherwise fall back to the
# original string behavior.
raw_body = (await api_response.content.read()).decode()
output_value = raw_body
try:
    parsed = json.loads(raw_body)
except (json.JSONDecodeError, ValueError):
    parsed = None
if isinstance(parsed, list) and parsed and all(
    isinstance(b, dict)
    and b.get("type") in ("input_text", "input_image", "input_file")
    for b in parsed
):
    output_value = parsed

tool_response = NeMoGymFunctionCallOutput(
    type="function_call_output",
    call_id=output_function_call.call_id,
    output=output_value,
)
```

---

## Patch 3 — local marketplace (`resources_server/app.py`)

**Location:** `/Users/ashijain/Documents/projectdealpoc/project_deal_approach_1/resources_server/app.py`

Lives in this repo so it's tracked normally. The function `_state_snapshot()`
returns a multimodal content list when at least one active listing has an
`image_path`. Falls back to the plain dict (text-only response) otherwise,
preserving Phase 1/2 behavior.

`_encode_image_to_data_url()` helper added in the same file resolves
project-relative paths and base64-encodes the JPEG.

---

## Verifying the patches are in place

```bash
cd /Users/ashijain/Documents/nemo_gym_lib
# Patch 1 marker
grep -n "LOCAL PATCH 2026-05-17" nemo_gym/openai_utils.py
# Patch 2 marker
grep -n "LOCAL PATCH 2026-05-17" responses_api_agents/simple_agent/app.py

cd /Users/ashijain/Documents/projectdealpoc/project_deal_approach_1
# Patch 3 marker
grep -n "Phase 3 multimodal" resources_server/app.py
```

All three greps should return non-empty.

After a `git pull` in NeMo Gym that removes either marker, re-apply that
patch from this file before running Phase 3.

---

## Rollback / disable

If multimodal causes issues at run time (token blowup, OpenRouter errors),
disable by short-circuiting the marketplace at patch 3:

```python
def _state_snapshot(state: MarketplaceState) -> dict:
    ...
    return snapshot   # always return dict; skip the multimodal branch
```


gent identities,
  model pairings, and random seeds are held fixed across all runs, so that
  observed differences in behavior trace to a single controlled variable: the
  market design.
  explain this 

  \textsc{S\,vs\,H}
  (Sonnet focal, Haiku field), \textsc{H\,vs\,S} (Haiku focal, Sonnet field),
  \textsc{S\,vs\,S}, and \textsc{H\,vs\,H} 
  why write cvc hvs 
  how will that we looking in paper ?

  how 40 rollout 
  only 20 rollout per phase i told or in toatal it should be 6 do you understand 

    The five sets differ deliberately in structural difficulty. Set~01 contains
  deals whose price ranges do not overlap, making certain trades impossible
  regardless of negotiation skill, and serves as a test of whether agents
  recognise and abandon structurally dead threads. Set~02 provides near-perfect
  through~05 introduce sparse matching, multi-buyer competition for a single
  scarce item, and chain-structured dependencies in which one deal must close
  before another becomes viable. Together these structures ensure that findings
  reflect general negotiation behavior rather than a single market configuration.
here wither write about all sets or give overwiew of 5 sets 


- instead of anthropic api it should be openrouter
- write eg in persona
- stimulation infra make more short 
