"""Runtime patches for the vendored NeMo Gym, applied before any of its code runs.

NeMo Gym's own source is never edited — it stays a clean vendored copy. Instead
`restart_ng_run.sh` installs this package plus `zz_nemo_gym_patches.pth` into each
subserver venv's site-packages, and site.py executes the .pth's import line at startup.

DO NOT go back to `sitecustomize.py`, which is what this used to use. Python imports
exactly ONE module by that name — the first on sys.path — and Ubuntu ships
`/usr/lib/python3.12/sitecustomize.py` (the apport hook) on a path entry that precedes
every venv's site-packages. So a venv-local sitecustomize.py is silently shadowed and
never runs. It worked on macOS, which ships no system sitecustomize, and has been dead on
Linux ever since the port. A .pth is not shadowable: site.py executes every .pth it finds
in site-packages. The `zz_` prefix orders it after the `__editable__*.pth` that installs
nemo_gym's import hook, which the patches need in place before they can import it.

ADDING A PATCH: drop a new module in this directory exposing `apply_patch()`. That is the
whole contract — `_discover()` picks it up. Do NOT reach for the old approach of copying a
patch file onto the loader itself: that is a single filename, so the second patch would
silently delete the first, and the model it was fixing would start failing again with no
error and no obvious cause.

WHAT BELONGS HERE: schema WIDENINGS — making NeMo Gym accept a value it currently rejects.
Those are safe for every model, which is why installation is unconditional. A patch that
narrows or reroutes behaviour does not belong here; it would need gating, and gating is
what made the previous version lie about its own state.
"""

import importlib
import pkgutil

_TAG = "[nemo_gym_patches]"

# Debian's patched site.py walks a venv's site-packages more than once, so the .pth line
# fires twice. The patches are idempotent, but running them twice logs twice and reads as
# a bug in the log — so the first result is remembered and returned.
_RESULT = None


def _discover():
    """Every sibling module in this package, imported. Order is alphabetical, so a patch
    must not depend on another having run first."""
    mods = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        mods.append(importlib.import_module(f"{__name__}.{info.name}"))
    return mods


def apply_all():
    """Apply every patch. One failure costs that patch only — the servers still have to
    boot, and a stack that refuses to start is worse than a stack missing one widening."""
    global _RESULT
    if _RESULT is not None:
        return _RESULT
    applied, failed = [], []
    for mod in _discover():
        name = mod.__name__.rsplit(".", 1)[-1]
        try:
            mod.apply_patch()
            applied.append(name)
        except Exception as e:  # noqa: BLE001 - a broken patch must not block the boot
            failed.append(name)
            print(f"{_TAG} WARNING: {name} failed: {e!r}")
    if applied:
        print(f"{_TAG} applied: {', '.join(applied)}")
    _RESULT = {"applied": applied, "failed": failed}
    return _RESULT
