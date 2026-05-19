"""
Deterministic focal-persona picker for Phase 1.

Rule: pick 3 personas per set using random.seed(seed). For sets 3, 4, 5
(which contain private-bearing personas), at least 1 of the 3 chosen
focals must have the `private` field. If random selection misses, force-
replace the last chosen non-private persona with a random private one.
"""

import random
from typing import Optional

# Sets that require at least one private-bearing focal
PRIVATE_REQUIRED_SETS = {"set_03", "set_04", "set_05"}


def _has_private(persona: dict) -> bool:
    return bool(persona.get("private"))


def select_focal_personas(
    personas: list[dict],
    set_id: str,
    seed: int,
    n_focal: int = 3,
) -> list[dict]:
    """Pick `n_focal` personas with deterministic seeded shuffle, enforcing
    the privacy constraint for sets 3-5."""
    if len(personas) < n_focal:
        raise ValueError(f"Need at least {n_focal} personas, got {len(personas)}")

    rng = random.Random(seed)
    pool = list(personas)
    rng.shuffle(pool)
    chosen = pool[:n_focal]

    if set_id in PRIVATE_REQUIRED_SETS and not any(_has_private(p) for p in chosen):
        # Force-replace: pick a private-bearing persona at random from the
        # remaining pool and swap it in for the last chosen non-private.
        remaining_private = [p for p in pool[n_focal:] if _has_private(p)]
        if not remaining_private:
            raise RuntimeError(
                f"Set {set_id} has no private-bearing personas to force-replace with"
            )
        swap_in = rng.choice(remaining_private)
        # Replace the last chosen (which is non-private) with swap_in
        chosen[-1] = swap_in

    return chosen
