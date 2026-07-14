"""The Save-result toggle, and the positional contract it rides on.

/run_live's inputs are POSITIONAL — the browser submits an array. If serve.py and app.js
ever disagree on the order or the count, every argument shifts by one and the run executes
with the wrong parameters, silently. So the two are pinned to each other here.
"""

import inspect
import re
from pathlib import Path

from sim_ui import live_runner, serve


ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "sim_ui" / "web" / "app.js"


def _params(**over):
    base = dict(phase="market_deal", set="01", focal="sonnet", opponent="gemini",
                max_turns=20, seed=42, scammer=True)
    base.update(over)
    return base


def test_a_run_is_not_recorded_by_default():
    assert "--record" not in live_runner._build_adapter_cmd(_params())
    assert "--record" not in live_runner._build_adapter_cmd(_params(record=False))


def test_the_toggle_asks_the_adapter_to_record():
    assert "--record" in live_runner._build_adapter_cmd(_params(record=True))


def test_the_backend_reads_the_toggle_as_off_unless_it_says_on():
    """Anything that is not "on" means do not keep this run."""
    src = inspect.getsource(serve._gradio_backend)
    assert '"record": (str(record).lower() == "on")' in src


def test_serve_and_app_js_agree_on_the_positional_inputs():
    """The failure this prevents is silent: every argument shifts by one."""
    src = inspect.getsource(serve._gradio_backend)
    params = [
        p.strip()
        for p in re.search(r"def run_live\(([^)]*)\)", src).group(1).split(",")
    ]
    inputs = [
        i.strip()
        for i in re.search(r"inputs=\[([^\]]*)\]", src).group(1).split(",")
    ]
    assert len(params) == len(inputs) == 8, (params, inputs)

    submitted = re.search(
        r'client\.submit\("/run_live",\s*\[(.*?)\]\)', APP_JS.read_text(), re.S
    )
    assert submitted, "the front-end no longer submits /run_live as an array"
    # count the top-level commas in the submitted array
    body = re.sub(r"\([^)]*\)", "", submitted.group(1))  # ignore commas inside calls
    n_submitted = len([a for a in body.split(",") if a.strip()])
    assert n_submitted == len(params), (
        f"app.js submits {n_submitted} arguments but serve.py takes {len(params)} — "
        "every argument after the mismatch is bound to the wrong parameter"
    )


def test_the_toggle_is_offered_in_the_ui_and_defaults_to_off():
    js = APP_JS.read_text()
    assert "cur.record=this.checked" in js, "the switch does not update the record flag"
    assert "cur.record===true?'on':'off'" in js, "the flag is not submitted"
    # unchecked unless explicitly on — a run is kept only when it is asked for
    assert "cur.record===true?'checked':''" in js, "the switch does not default to off"


def test_the_switch_explains_itself_on_hover():
    """The reason lives in a tooltip, not a line of text parked in the control bar."""
    js = APP_JS.read_text()
    css = (ROOT / "sim_ui" / "web" / "index.html").read_text()

    assert 'class="swwrap" data-tip=' in js, "the switch has no hover explanation"
    assert ".swwrap:hover::after" in css, "the tooltip never becomes visible"


def test_the_tooltip_describes_the_state_it_is_in():
    """Hovering an ON switch must not read out the OFF explanation, and vice versa."""
    js = APP_JS.read_text()

    tip = re.search(r'class="swwrap" data-tip="(.*?)">', js, re.S)
    assert tip, "the tooltip is gone"
    body = tip.group(1)
    assert "cur.record===true" in body, "the tooltip says the same thing in both states"
    assert "ON —" in body and "OFF —" in body, "each state needs its own wording"
