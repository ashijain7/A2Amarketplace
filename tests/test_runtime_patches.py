"""Runtime patches must accumulate, not replace each other.

NeMo Gym is vendored and unmodified; model-specific fixes reach it through a
`sitecustomize.py` that Python's site.py auto-imports at venv startup. That filename is
singular, and the installer used to `cp` one patch file onto it — so the day a second
model needs a different fix, whoever writes patch #2 copies it over patch #1 and Opus 4.7
silently starts failing validation again. No error, no warning, and the symptom appears in
a model nobody was working on.

So sitecustomize is now a loader over a `nemo_gym_patches` package: a new fix is a new
module, never a replacement. Installation is also unconditional. Every patch here only
WIDENS a schema (accepts a value it used to reject), which no model can be broken by, and
the old `if focal is opus` branch left the previous run's patch in place while printing
"skipping runtime patch" — a log that disagreed with both reality and NeMo Gym's own
"[patch] applied" line in the same file.
"""

import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import nemo_gym_patches  # noqa: E402

RESTART_SH = (ROOT / "scripts" / "restart_ng_run.sh").read_text()
# Comments there quote the old behaviour on purpose (that is the record of why it
# changed), so the gate assertions read the executable lines only.
RESTART_CODE = "\n".join(
    l for l in RESTART_SH.splitlines() if not l.lstrip().startswith("#")
)


@pytest.fixture(autouse=True)
def _fresh():
    """apply_all() memoizes, so each test starts from an unapplied state."""
    nemo_gym_patches._RESULT = None
    yield
    nemo_gym_patches._RESULT = None


def _fake(name, applied, fail=False):
    mod = types.ModuleType(name)

    def apply_patch():
        if fail:
            raise RuntimeError("boom")
        applied.append(name)

    mod.apply_patch = apply_patch
    return mod


def test_every_patch_module_is_applied(monkeypatch):
    applied = []
    mods = [_fake("one", applied), _fake("two", applied)]
    monkeypatch.setattr(nemo_gym_patches, "_discover", lambda: mods)

    result = nemo_gym_patches.apply_all()

    assert applied == ["one", "two"]
    assert result["applied"] == ["one", "two"]


def test_a_broken_patch_does_not_stop_the_others(monkeypatch):
    """A failed patch must cost us that one fix, not the whole stack — the servers still
    have to boot."""
    applied = []
    mods = [_fake("bad", applied, fail=True), _fake("good", applied)]
    monkeypatch.setattr(nemo_gym_patches, "_discover", lambda: mods)

    result = nemo_gym_patches.apply_all()

    assert result["applied"] == ["good"]
    assert result["failed"] == ["bad"]


def test_applying_twice_patches_once(monkeypatch):
    """Debian's site.py walks a venv's site-packages twice, so the .pth line fires twice.
    Harmless — the patches are idempotent — but a doubled log reads as a bug."""
    applied = []
    monkeypatch.setattr(nemo_gym_patches, "_discover", lambda: [_fake("one", applied)])

    nemo_gym_patches.apply_all()
    nemo_gym_patches.apply_all()

    assert applied == ["one"]


def test_the_service_tier_patch_ships_in_the_package():
    names = [m.__name__.rsplit(".", 1)[-1] for m in nemo_gym_patches._discover()]

    assert "service_tier" in names


def test_the_service_tier_patch_widens_the_field():
    from nemo_gym.openai_utils import NeMoGymResponse
    from nemo_gym_patches import service_tier

    service_tier.apply_patch()

    NeMoGymResponse.model_fields["service_tier"].annotation  # present and readable
    assert NeMoGymResponse.model_fields["service_tier"].default is None


def test_the_installer_copies_the_whole_package_not_one_file():
    assert "nemo_gym_patches" in RESTART_CODE
    assert "nemo_gym_runtime_patch.py" not in RESTART_CODE, "the single-file copy is gone"


def test_the_loader_is_a_pth_because_sitecustomize_is_shadowed_on_linux():
    """Python imports exactly one `sitecustomize` — the first on sys.path — and Ubuntu
    ships /usr/lib/python3.12/sitecustomize.py on a path entry ahead of every venv's
    site-packages. A venv-local one is never imported, which is why the Opus fix was
    silently inactive on Linux. site.py executes every .pth it finds, so a .pth cannot be
    shadowed the same way."""
    assert (ROOT / "scripts" / "zz_nemo_gym_patches.pth").exists()
    assert "zz_nemo_gym_patches.pth" in RESTART_CODE
    installs_sitecustomize = [
        l for l in RESTART_CODE.splitlines()
        if "sitecustomize.py" in l and "rm -f" not in l
    ]
    assert installs_sitecustomize == [], "nothing may be installed as sitecustomize.py"


def test_the_pth_runs_after_the_editable_install_hook():
    """site.py processes .pth files in sorted order. nemo_gym is an editable install whose
    import hook arrives via `__editable__*.pth`; our patches import nemo_gym, so ours has
    to sort after it."""
    assert sorted(["__editable__.nemo_gym.pth", "zz_nemo_gym_patches.pth"])[-1] == (
        "zz_nemo_gym_patches.pth"
    )


def test_the_installer_is_not_gated_on_the_focal_model():
    """The patches only widen schemas, so there is no model they can harm — and gating
    left a stale patch installed while claiming it had been skipped."""
    assert 'grep -qi "opus"' not in RESTART_CODE
    assert "skipping runtime patch" not in RESTART_CODE
