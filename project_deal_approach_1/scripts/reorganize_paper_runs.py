"""
Reorganize the paper_runs directory into per-rollout folders.

Before:
    results/paper_runs/<config>/phase<N>/
        rollouts.jsonl
        per_set/set_NN_channel.jsonl  (partial files)
        ...

After:
    results/paper_runs/<config>/phase<N>/
        set_01_Kai/
            channel.jsonl
            deals.json
            judge_ratings.json
            personas.json
            rollout.json
            rubric_scores.json
            summary.json
        set_02_Rex/
            (same 7)
        ... (5 set folders per phase)
        rollouts.jsonl       (kept — canonical raw data)
        aggregate.json       (kept — phase-level summary)
        INSIGHTS.md          (kept — writeup)

The per-rollout files come from results/runs/ (created by archive_run.py).
We copy them into the right paper_runs phase folder under a clean
`set_NN_<focal>/` name.

One special case:
  - C1 P2 set_01 (Kai) was killed mid-flight and salvaged post-hoc. There's
    no archive for it in results/runs/. We reconstruct the 7 files from the
    salvaged row in rollouts_truncated.jsonl.

Usage:
    python scripts/reorganize_paper_runs.py
"""

import json
import re
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ARCHIVES_DIR = PROJECT / "results" / "runs"
PAPER_RUNS_DIR = PROJECT / "results" / "paper_runs"

# Map archive's config tag (e.g. "focal-S-vs-S") to paper_runs config dir
CONFIG_DIR_MAP = {
    "focal-S-vs-S": "C1_sonnet_vs_sonnet",
    "focal-S-vs-G": "C4_sonnet_vs_gemini",
    "focal-O-vs-G": "C6_opus_vs_gemini",
    "focal-G-vs-X": "C7_gemini_vs_gpt55",
    "focal-G35-vs-X": "C8_gemini35_vs_gpt55",
}

# Inverse for the salvaged-Kai special case
CONFIG_NAME_TO_DIR = {
    "focal_S_vs_S": "C1_sonnet_vs_sonnet",
    "focal_S_vs_G": "C4_sonnet_vs_gemini",
    "focal_O_vs_G": "C6_opus_vs_gemini",
    "focal_G_vs_X": "C7_gemini_vs_gpt55",
    "focal_G35_vs_X": "C8_gemini35_vs_gpt55",
}

# Pattern: a1_phase{N}_focal-X-vs-Y_set{NN}_focal-{Name}_seed{S}_{TIMESTAMP}
# The focal side can be alphanumeric (e.g. "G35") to support the C8 config.
ARCHIVE_NAME_RE = re.compile(
    r"^a1_phase(?P<phase>\d+)_(?P<config_tag>focal-[A-Z][A-Z0-9]*-vs-[A-Z])_"
    r"set(?P<setn>\d+)_focal-(?P<focal>[^_]+)_seed(?P<seed>\d+)_"
    r"(?P<timestamp>\d{8}_\d{4})$"
)

REQUIRED_FILES = [
    "channel.jsonl",
    "deals.json",
    "judge_ratings.json",
    "personas.json",
    "rollout.json",
    "rubric_scores.json",
    "summary.json",
]


def copy_archive_to_paper_runs(archive_path: Path) -> tuple[str, str] | None:
    """Copy one archived run into the paper_runs structure.
    Returns (config_dir, set_folder_name) on success, None on failure."""
    m = ARCHIVE_NAME_RE.match(archive_path.name)
    if not m:
        print(f"  SKIP (unparseable name): {archive_path.name}")
        return None

    phase = int(m.group("phase"))
    config_tag = m.group("config_tag")
    setn = m.group("setn")
    focal = m.group("focal")

    config_dir = CONFIG_DIR_MAP.get(config_tag)
    if config_dir is None:
        print(f"  SKIP (unknown config_tag {config_tag}): {archive_path.name}")
        return None

    set_folder = f"set_{setn}_{focal}"
    dest_dir = PAPER_RUNS_DIR / config_dir / f"phase{phase}" / set_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy each required file
    for fname in REQUIRED_FILES:
        src = archive_path / fname
        dst = dest_dir / fname
        if src.exists():
            shutil.copy2(src, dst)
        else:
            print(f"  WARN: {archive_path.name} missing {fname}")

    return (config_dir, set_folder)


def reconstruct_kai_c1p2(rollouts_truncated_path: Path) -> bool:
    """Reconstruct the missing C1 P2 Kai run from rollouts_truncated.jsonl.

    Builds the 7 canonical files from the salvaged rollout row.
    """
    rollouts = [json.loads(l) for l in rollouts_truncated_path.open()]
    kai_row = None
    for r in rollouts:
        md = r.get("metadata", {})
        if md.get("set_id") == "set_01" and md.get("focal_persona") == "Kai":
            kai_row = r
            break
    if kai_row is None:
        print("  ERROR: Kai not in rollouts_truncated.jsonl")
        return False

    dest_dir = PAPER_RUNS_DIR / "C1_sonnet_vs_sonnet" / "phase2" / "set_01_Kai"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # channel.jsonl
    with (dest_dir / "channel.jsonl").open("w") as f:
        for ev in kai_row.get("channel_events", []) or []:
            f.write(json.dumps(ev) + "\n")

    # deals.json — wrap as {"deals": [...]} to match archive format
    deals_list = kai_row.get("deals", []) or []
    with (dest_dir / "deals.json").open("w") as f:
        json.dump({"deals": deals_list, "fulfilled_want_ids": []}, f, indent=2)

    # personas.json
    with (dest_dir / "personas.json").open("w") as f:
        json.dump(kai_row.get("personas", []), f, indent=2)

    # rubric_scores.json
    with (dest_dir / "rubric_scores.json").open("w") as f:
        json.dump(kai_row.get("rubric_scores", {}), f, indent=2)

    # judge_ratings.json — extracted from capability_asymmetry + privacy
    rs = kai_row.get("rubric_scores", {}) or {}
    ca = rs.get("capability_asymmetry") or {}
    pr = rs.get("privacy") or {}
    judge_ratings = {
        "self_rating": ca.get("self_rating"),
        "observer_rating": ca.get("observer_rating"),
        "perceived_fairness": ca.get("perceived_fairness"),
        "boundary_score": pr.get("boundary_score"),
        "leak_details": pr.get("leak_details"),
    }
    with (dest_dir / "judge_ratings.json").open("w") as f:
        json.dump(judge_ratings, f, indent=2)

    # rollout.json — preserve everything for completeness
    with (dest_dir / "rollout.json").open("w") as f:
        json.dump(kai_row, f, indent=2)

    # summary.json
    md = kai_row.get("metadata", {})
    summary = {
        "run_id": f"a1_phase2_focal-S-vs-S_set01_focal-Kai_seed42_SALVAGED",
        "approach": 1,
        "phase": 2,
        "timestamp": "2026-05-20T17:43:00Z",
        "config": {
            "model_config": md.get("config_name"),
            "focal_model": "anthropic/claude-sonnet-4-5",
            "opponents_model": "anthropic/claude-sonnet-4-5",
            "judge_model": "openai/gpt-4o-2024-11-20",
            "persona_set": md.get("set_id"),
            "focal_persona": md.get("focal_persona"),
            "seed": md.get("seed"),
        },
        "rubric_scores": {
            "deal_outcomes": (rs.get("deal_outcomes") or {}).get("combined"),
            "capability_asymmetry": (rs.get("capability_asymmetry") or {}).get("combined"),
            "negotiation_quality": (rs.get("negotiation_quality") or {}).get("combined"),
            "privacy": (rs.get("privacy") or {}).get("combined"),
            "review_utilization": (rs.get("review_utilization") or {}).get("combined"),
            "final_reward": kai_row.get("reward"),
        },
        "focal_value_extracted": ca.get("focal_value_extracted"),
        "deal_count": len(deals_list),
        "salvage_note": "Original rollout was killed mid-flight at event 328+; truncated to first 100 events and rubrics re-scored.",
    }
    with (dest_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"  ✓ reconstructed: C1_sonnet_vs_sonnet/phase2/set_01_Kai (salvaged)")
    return True


def cleanup_redundant_files(config_dir: str, phase: int):
    """Remove the old per_set/ folder now that per-rollout folders exist."""
    base = PAPER_RUNS_DIR / config_dir / f"phase{phase}"
    old_per_set = base / "per_set"
    if old_per_set.exists():
        shutil.rmtree(old_per_set)
        print(f"  removed redundant: {config_dir}/phase{phase}/per_set/")


def main():
    print(f"Reading archives from: {ARCHIVES_DIR}")
    print(f"Writing to: {PAPER_RUNS_DIR}")
    print()

    if not ARCHIVES_DIR.exists():
        print(f"ERROR: {ARCHIVES_DIR} does not exist", file=sys.stderr)
        return 1

    # 1. Copy all archived runs into their paper_runs slot
    copied = []
    for archive_path in sorted(ARCHIVES_DIR.iterdir()):
        if not archive_path.is_dir():
            continue
        result = copy_archive_to_paper_runs(archive_path)
        if result:
            copied.append(result)

    print()
    print(f"Copied {len(copied)} archived runs into paper_runs/")

    # 2. Reconstruct missing C1 P2 Kai from salvaged data
    print()
    print("Reconstructing C1 P2 Kai from salvaged data...")
    salvage_path = PAPER_RUNS_DIR / "C1_sonnet_vs_sonnet" / "phase2" / "rollouts_truncated.jsonl"
    if salvage_path.exists():
        reconstruct_kai_c1p2(salvage_path)
    else:
        print(f"  WARN: salvaged data not found at {salvage_path}")

    # 3. Optional: clean up redundant per_set/ folders
    print()
    print("Cleaning up redundant per_set/ folders...")
    for config_dir in CONFIG_NAME_TO_DIR.values():
        for phase in [1, 2, 3]:
            cleanup_redundant_files(config_dir, phase)

    # 4. Final summary
    print()
    print("=" * 60)
    print("Final structure:")
    print("=" * 60)
    for config_dir in sorted(CONFIG_NAME_TO_DIR.values()):
        for phase in [1, 2, 3]:
            phase_dir = PAPER_RUNS_DIR / config_dir / f"phase{phase}"
            if not phase_dir.exists():
                continue
            set_dirs = sorted(d.name for d in phase_dir.iterdir() if d.is_dir())
            print(f"  {config_dir}/phase{phase}/")
            for s in set_dirs:
                print(f"    {s}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
