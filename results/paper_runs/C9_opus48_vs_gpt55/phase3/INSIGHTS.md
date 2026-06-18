# INSIGHTS — focal_O_vs_X / phase 3

**Focal model:** anthropic/claude-opus-4.8
**Opponents:** see model_config.py for the field
**Rollouts:**        5 (one per persona set, seed 42)
**Spend:** $59.369148
**Wall time:** 1767s

## Aggregate

```
{
  "config_name": "focal_O_vs_X",
  "phase": 3,
  "focal_model": "anthropic/claude-opus-4.8",
  "rollout_count": 5,
  "mean_reward": 0.65226,
  "min_reward": 0.4154,
  "max_reward": 0.8055
}
```

## Per-rollout summary

| set | focal | reward | deals | events |
|-----|-------|-------:|------:|-------:|
| set_05 | Taj | 0.796 | 1 | 12 |
| set_04 | Buck | 0.787 | 2 | 50 |
| set_01 | Rosa | 0.457 | 3 | 50 |
| set_03 | Zara | 0.805 | 2 | 94 |
| set_02 | Rex | 0.415 | 3 | 98 |

## Findings

**Opus-4.8 self-terminates early in swapshop (model-behavior finding).** In 3 of 5 sets the focal
ended the rollout by writing a wrap-up message instead of calling a tool. There is no explicit
"end" tool (tools: post_listing / propose_swap / accept_swap / reject_swap / pass / lookup_agent),
so the harness ends a rollout the moment the focal stops calling tools — the message ends it.
Tool calls made before stopping (50-step cap): Taj 8, Rosa 27, Buck 27; Rex and Zara ran the full 50.

By contrast, Opus-4.7 (C6) and Gemini-3.1-Pro (C7) never declared "done" — all five of their
phase-3 sets ran to the cap (~96–100 channel events each). So C9's short rollouts reflect an
Opus-4.8 trait (it judges its trading complete and stops), not a harness or scoring failure.

Effect on the data: C9 phase-3 channel lengths span 12–98 events vs ~100 for the reference
configs; the short sets (Taj 12, Rosa/Buck 50) cover fewer turns and are not length-comparable to
those configs. Left as-is (not re-run) and recorded as a behavioral finding.

## Notable rollouts

- **set_05 Taj (12 events, 1 deal):** after a single swap (White Sweater → Brown Floral Dress, a net
  value gain), the focal wrote *"My business is fully complete…"* and stopped — the earliest self-termination.

