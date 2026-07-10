"""
Gradio dashboard for the Agent-to-Agent Marketplace.

One mode-agnostic dispatcher streams an episode turn-by-turn into a gr.HTML,
with the same "thinking / searching" beats as the approved mockup. Cached mode
replays the recorded rollouts; Live is stubbed for the adapter wiring (Step 3b).
"""
from __future__ import annotations

import time

import gradio as gr

from . import render
from .logic import Catalog, load_episode, models_for, MODE_LABEL, MODES

# ---- pacing (seconds) — matches the tuned mockup feel -----------------------
BEAT_SEARCH = 1.8      # opponent about to reply / searching the marketplace
BEAT_THINK = 1.5       # focal about to reply
AFTER_FOCAL = 0.7      # linger after a focal bubble
AFTER_OPP = 0.5        # linger after an opponent bubble
REVIEW_BEAT = 1.1
ROOM_DIVIDER = 0.9
ROOM_REPLY = 1.6
AFTER_ROOM = 0.8
DEAL_GAP = 0.6
END_BEAT = 0.5

CAT = Catalog()


def _config_choices(mode: str):
    """(label, value) pairs for the config dropdown — value is the slug."""
    out = []
    for c in CAT.configs(mode):
        fm, om = models_for(c)
        out.append((f"{fm}  vs  {om}", c))
    return out


def _first(seq, default=None):
    return seq[0] if seq else default


# ---- the streaming replay dispatcher ---------------------------------------
def run_episode(mode: str, config: str, set_id: str):
    """Generator yielding (conversation_html, reward_html) turn by turn."""
    entry = CAT.find(mode, config, set_id)
    if entry is None:
        yield render.sim_card('<div class="empty">No cached run for this selection.</div>'), render.reward_pending()
        return
    ep = load_episode(entry)

    pre = [render.card_header(ep)]
    deals_state = []   # list of dicts: {deal, convo:[frag], outcome:str}

    def card_html() -> str:
        body = "".join(pre)
        for st in deals_state:
            body += render.deal_header(st["i"], st["deal"], ep.focal)
            body += '<div class="convo">' + "".join(st["convo"]) + "</div>"
            body += st["outcome"]
        if ep.deals and all(st["outcome"] for st in deals_state) and len(deals_state) == len(ep.deals):
            body += render.episode_summary(ep)
        return render.sim_card(body)

    yield card_html(), render.reward_pending()

    if ep.mode == "review":
        pre.append(render.rep_bubble())
        yield card_html(), render.reward_pending()
        time.sleep(REVIEW_BEAT)

    if not ep.deals:
        pre.append(render.empty_state(ep.focal))
        yield card_html(), render.reward_pending()
        time.sleep(END_BEAT)
        yield card_html(), render.reward_panel(ep)
        return

    for i, d in enumerate(ep.deals):
        st = {"i": i, "deal": d, "convo": [], "outcome": ""}
        deals_state.append(st)
        convo = st["convo"]
        yield card_html(), render.reward_pending()

        prev = None
        first_wait = True
        for t in d.thread:
            is_f = (t.agent == ep.focal)
            if prev is not None and is_f != prev:
                if is_f:
                    convo.append(render.wait_row(f"💭 {ep.focal} is thinking"))
                    yield card_html(), render.reward_pending()
                    time.sleep(BEAT_THINK)
                    convo.pop()
                else:
                    who = "a buyer" if d.seller == ep.focal else "a seller"
                    txt = f"🔍 searching the marketplace for {who}" if first_wait else f"💬 {t.agent} is replying"
                    first_wait = False
                    convo.append(render.wait_row(txt))
                    yield card_html(), render.reward_pending()
                    time.sleep(BEAT_SEARCH)
                    convo.pop()
            convo.append(render.bubble(t, ep.focal))
            yield card_html(), render.reward_pending()
            time.sleep(AFTER_FOCAL if is_f else AFTER_OPP)
            prev = is_f

        if d.room:
            convo.append(render.divider_public())
            convo.append(render.divider_room())
            yield card_html(), render.reward_pending()
            time.sleep(ROOM_DIVIDER)
            rprev = None
            for r in d.room:
                is_f = (r.speaker == ep.focal)
                if rprev is not None and is_f != rprev:
                    txt = f"💭 {ep.focal} is thinking" if is_f else f"💬 {r.speaker} is replying"
                    convo.append(render.wait_row(txt))
                    yield card_html(), render.reward_pending()
                    time.sleep(BEAT_THINK if is_f else ROOM_REPLY)
                    convo.pop()
                extra = "scam" if r.is_scammer else ""
                convo.append(render.bubble(_room_turn(r), ep.focal, extra))
                if r.is_scammer:
                    convo.append(render.scam_caption(d.seller))
                yield card_html(), render.reward_pending()
                time.sleep(AFTER_ROOM)
                rprev = is_f

        st["outcome"] = render.deal_outcome(d, ep.focal)
        yield card_html(), render.reward_pending()
        time.sleep(DEAL_GAP)

    time.sleep(END_BEAT)
    yield card_html(), render.reward_panel(ep)


def _room_turn(r):
    from .logic import Turn
    return Turn(agent=r.speaker, action="say_in_room", price=None, message=r.text)


# ---- Blocks layout ---------------------------------------------------------
HEADER = (
    '<div id="a2a-hdr" style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;'
    'padding:6px 2px 2px">'
    '<h1 style="font-size:26px;font-weight:750;letter-spacing:-.01em;margin:0;color:#13213c">'
    'Agent-to-Agent Marketplace</h1>'
    '<span style="color:#6b7480;font-size:14px">evaluated agent vs 9 opponents · cached replay</span></div>'
)


def build_demo() -> gr.Blocks:
    modes = CAT.modes()
    default_mode = _first(modes, "market")
    default_cfgs = _config_choices(default_mode)
    default_cfg = _first([v for _, v in default_cfgs])
    default_sets = CAT.sets(default_mode, default_cfg) if default_cfg else []
    default_set = _first(default_sets)

    with gr.Blocks(css=render.CSS, title="Agent-to-Agent Marketplace",
                   theme=gr.themes.Soft(primary_hue="blue")) as demo:
        with gr.Column(elem_id="a2a-root"):
            gr.HTML(HEADER)
            with gr.Tabs():
                with gr.TabItem("Simulation"):
                    with gr.Row():
                        gr.Dropdown(["Cached"], value="Cached", label="Mode", interactive=False, scale=1)
                        stage_dd = gr.Dropdown([(MODE_LABEL[m], m) for m in modes], value=default_mode,
                                               label="Stage", scale=1)
                        config_dd = gr.Dropdown(default_cfgs, value=default_cfg,
                                                label="Evaluated vs Opponent", scale=2)
                        set_dd = gr.Dropdown(default_sets, value=default_set, label="Scenario set", scale=1)
                        run_btn = gr.Button("Replay", variant="primary", scale=1)
                    with gr.Row(equal_height=False):
                        convo_html = gr.HTML(render.sim_card(""), elem_id="a2a-convo")
                        reward_html = gr.HTML(render.reward_pending(), elem_id="a2a-reward")
                with gr.TabItem("Verifiers & Rewards"):
                    gr.HTML(render.verifier_page())

        # ---- dependent dropdown wiring ----
        def on_stage(mode):
            cfgs = _config_choices(mode)
            cfg = _first([v for _, v in cfgs])
            sets = CAT.sets(mode, cfg) if cfg else []
            return gr.update(choices=cfgs, value=cfg), gr.update(choices=sets, value=_first(sets))

        def on_config(mode, cfg):
            sets = CAT.sets(mode, cfg) if cfg else []
            return gr.update(choices=sets, value=_first(sets))

        stage_dd.change(on_stage, inputs=stage_dd, outputs=[config_dd, set_dd])
        config_dd.change(on_config, inputs=[stage_dd, config_dd], outputs=set_dd)
        run_btn.click(run_episode, inputs=[stage_dd, config_dd, set_dd], outputs=[convo_html, reward_html])

    return demo
