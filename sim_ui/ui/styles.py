"""The sim-UI stylesheet — ported verbatim from the approved mockup."""

CSS = r"""
:root{
  --bg:#f5f6f9; --card:#ffffff; --border:#e7e9ef; --border-soft:#eef0f4;
  --ink:#13213c; --body:#28303e; --muted:#6b7480; --faint:#9aa2ad;
  --blue:#2f62f4; --blue-ink:#2b53c9;
  --focal-bg:#e9eafc; --focal-ink:#23264a; --focal-av:#4b54cc;
  --opp-bg:#eef1f4; --opp-ink:#28303c; --opp-av:#98a0ad;
  --chip-bg:#fbe7b0; --chip-ink:#7c5c10;
  --rep-bg:#eef1ff; --rep-ink:#33449e; --star:#e0a100;
  --scam-bg:#fdeaec; --scam-ink:#b0342c; --scam-line:#e0524e;
  --good-bg:#e6f5ec; --good-ink:#177a3f;
  --neutral-bg:#eaeef6; --neutral-ink:#3b4658;
  --bad-bg:#fdeaec; --bad-ink:#b0342c;
  --pill-bg:#e8edff; --pill-ink:#2b53d6;
  --hyb:#6a54d6; --det:#7c8698;
}
#a2a-root{color:var(--body);font-size:15px;line-height:1.5}
#a2a-root h1,#a2a-root h2,#a2a-root h3,#a2a-root h4{color:var(--ink);margin:0}
#a2a-root .card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px 22px 18px;box-shadow:0 1px 2px rgba(19,33,60,.04)}
#a2a-root .eyebrow{color:var(--blue);font-size:12.5px;font-weight:700}
#a2a-root .card h2{font-size:20px;font-weight:750;margin:3px 0 4px}
#a2a-root .cfgrow{display:flex;align-items:center;gap:10px;margin:6px 0 8px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
#a2a-root .cfg{font-weight:700;color:var(--ink)} #a2a-root .cfg .ev{color:var(--blue-ink)}
#a2a-root .setpill{background:#eef0f4;color:var(--muted);font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:6px}
#a2a-root .dealhdr{display:flex;align-items:center;gap:9px;margin:20px 0 12px;padding-top:16px;border-top:1px solid var(--border-soft);flex-wrap:wrap}
#a2a-root .dealhdr:first-child{border-top:none;padding-top:6px;margin-top:8px}
#a2a-root .dnum{font-size:12px;font-weight:800;color:var(--muted);letter-spacing:.03em}
#a2a-root .dtag{font-size:10px;font-weight:800;letter-spacing:.04em;padding:2px 7px;border-radius:5px}
#a2a-root .dtag.sell{background:#e7ecf3;color:#4a5568} #a2a-root .dtag.buy{background:#e8edff;color:var(--pill-ink)}
#a2a-root .dwho{font-size:13.5px;font-weight:650;color:var(--ink)} #a2a-root .ditem{font-size:12.5px;color:var(--muted)}
#a2a-root .convo{display:flex;flex-direction:column;gap:14px}
#a2a-root .row{display:flex;gap:10px;align-items:flex-end;max-width:82%}
#a2a-root .row.opp{margin-left:auto;flex-direction:row-reverse}
#a2a-root .av{width:26px;height:26px;border-radius:50%;flex:0 0 26px;color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;margin-bottom:20px}
#a2a-root .row.focal .av{background:var(--focal-av)} #a2a-root .row.opp .av{background:var(--opp-av)}
#a2a-root .bwrap{display:flex;flex-direction:column;gap:6px;min-width:0}
#a2a-root .row.opp .bwrap{align-items:flex-end}
#a2a-root .bubble{padding:11px 14px;border-radius:15px;font-size:14px;line-height:1.5}
#a2a-root .row.focal .bubble{background:var(--focal-bg);color:var(--focal-ink);border-bottom-left-radius:5px}
#a2a-root .row.opp .bubble{background:var(--opp-bg);color:var(--opp-ink);border-bottom-right-radius:5px}
#a2a-root .chip{align-self:flex-start;background:var(--chip-bg);color:var(--chip-ink);font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:6px;font-variant-numeric:tabular-nums}
#a2a-root .row.opp .chip{align-self:flex-end}
#a2a-root .photo{width:118px;height:150px;border-radius:10px;object-fit:cover;margin-bottom:6px;border:1px solid var(--border)}
@keyframes a2apop{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
#a2a-root .row,#a2a-root .rep,#a2a-root .dealout{animation:a2apop .25s ease}
#a2a-root .rep{background:var(--rep-bg);border-radius:13px;padding:11px 14px;font-size:13.5px;margin-bottom:14px}
#a2a-root .rep b{color:var(--rep-ink)} #a2a-root .rep .star{color:var(--star);font-weight:700} #a2a-root .rep .q{color:var(--muted);font-style:italic}
#a2a-root .foot-note{color:var(--faint);font-size:11px;margin-top:3px}
#a2a-root .searching{display:flex;align-items:center;gap:9px;color:var(--muted);font-size:13px;padding:7px 2px;margin-left:36px}
#a2a-root .dots{display:inline-flex;gap:3px}
#a2a-root .dots i{width:6px;height:6px;border-radius:50%;background:var(--faint);animation:a2ab 1s infinite}
#a2a-root .dots i:nth-child(2){animation-delay:.15s}#a2a-root .dots i:nth-child(3){animation-delay:.3s}
@keyframes a2ab{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}
#a2a-root .seclabel{color:var(--muted);font-size:11.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin:12px 0 2px}
#a2a-root .divider{display:flex;align-items:center;gap:12px;color:var(--rep-ink);font-size:12px;font-weight:700;letter-spacing:.04em;margin:8px 0 2px}
#a2a-root .divider::before,#a2a-root .divider::after{content:"";flex:1;border-top:1px dashed #c7cbe6}
#a2a-root .row.scam .bubble{background:var(--scam-bg);color:var(--scam-ink);border:1px solid #f4c9cc;border-bottom-left-radius:5px}
#a2a-root .row.scam .av{background:var(--scam-line)}
#a2a-root .scamcap{color:var(--scam-ink);font-size:11.5px;font-style:italic;margin-left:36px;margin-top:-6px}
#a2a-root .dealout{margin-top:12px;border-radius:10px;padding:9px 13px;font-size:13px;font-weight:650}
#a2a-root .dealout.good{background:var(--good-bg);color:var(--good-ink)}
#a2a-root .dealout.neutral{background:var(--neutral-bg);color:var(--neutral-ink)}
#a2a-root .dealout.bad{background:var(--bad-bg);color:var(--bad-ink)}
#a2a-root .empty{margin:18px 0;border:1px dashed var(--border);border-radius:12px;padding:26px 18px;text-align:center;color:var(--muted);font-size:14px;background:#fbfbfd}
#a2a-root .empty b{color:var(--ink)}
#a2a-root .summary{margin-top:18px;border-top:1px solid var(--border-soft);padding-top:6px}
#a2a-root .summary .m{display:flex;justify-content:space-between;padding:9px 2px;border-bottom:1px solid var(--border-soft);font-size:13.5px}
#a2a-root .summary .m:last-child{border-bottom:none}
#a2a-root .summary .k{color:var(--muted)} #a2a-root .summary .v{font-weight:700;color:var(--ink)}
#a2a-root .panel h3{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:700;margin-bottom:14px}
#a2a-root .pending{display:flex;align-items:center;gap:10px;color:var(--faint);font-size:13.5px;padding:18px 0 6px}
#a2a-root .rhero{background:linear-gradient(180deg,#f3f6ff,#eef2fe);border:1px solid #dfe6fb;border-radius:14px;padding:16px 18px;margin-bottom:18px}
#a2a-root .rhero .big{display:flex;align-items:baseline;gap:8px}
#a2a-root .rhero .n{font-size:40px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.02em}
#a2a-root .rhero .l{color:var(--muted);font-size:12.5px;font-weight:600}
#a2a-root .rtrack{height:8px;background:#dde5fa;border-radius:99px;overflow:hidden;margin:12px 0 6px}
#a2a-root .rtrack .rfill{height:100%;border-radius:99px;background:linear-gradient(90deg,#4f7dff,#2f62f4);transition:width 1s cubic-bezier(.4,0,.2,1)}
#a2a-root .rhero .cap{color:var(--muted);font-size:11.5px}
#a2a-root .rrow{padding:12px 0;border-bottom:1px solid var(--border-soft)}
#a2a-root .rrow:last-child{border-bottom:none}
#a2a-root .rline{display:flex;align-items:center;gap:8px;margin-bottom:6px}
#a2a-root .rdot{width:8px;height:8px;border-radius:50%;flex:0 0 8px}
#a2a-root .rdot.det{background:var(--det)} #a2a-root .rdot.hyb{background:var(--hyb)}
#a2a-root .rname{font-size:13.5px;font-weight:650;color:var(--ink)}
#a2a-root .rw{font-size:10.5px;color:var(--pill-ink);background:var(--pill-bg);border-radius:5px;padding:1px 6px;font-weight:700;font-variant-numeric:tabular-nums}
#a2a-root .rscore{margin-left:auto;font-size:14px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
#a2a-root .bar{height:7px;background:#eef0f4;border-radius:99px;overflow:hidden}
#a2a-root .fill{height:100%;border-radius:99px;background:var(--blue);transition:width .9s cubic-bezier(.4,0,.2,1)}
#a2a-root .rmeta{display:flex;justify-content:space-between;gap:10px;margin-top:6px;font-size:11.5px;color:var(--muted)}
#a2a-root .rmeta .contrib{color:var(--blue-ink);font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
#a2a-root .callout{background:var(--rep-bg);border-radius:12px;padding:14px 16px;font-size:13px;color:#38416a;margin-top:12px}
#a2a-root .callout b{color:var(--rep-ink)}
#a2a-root .sech{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:10px}
#a2a-root .legend{display:flex;gap:16px;margin:14px 0 2px;font-size:12px;color:var(--muted);flex-wrap:wrap}
#a2a-root .legend span{display:inline-flex;align-items:center;gap:6px}
#a2a-root .legend .d{width:9px;height:9px;border-radius:50%}
#a2a-root .rewardformula{display:flex;align-items:center;justify-content:center;gap:14px;flex-wrap:wrap;background:#f3f6ff;border:1px solid #dfe6fb;border-radius:12px;padding:16px;margin:14px 0 4px}
#a2a-root .rf-frac{display:flex;flex-direction:column;align-items:center}
#a2a-root .rf-line{border-top:2px solid var(--ink);width:100%;margin:4px 0}
#a2a-root .rf-big{font-size:15px;font-weight:700;color:var(--ink);white-space:nowrap}
#a2a-root .rf-eq{font-size:22px;font-weight:800;color:var(--blue-ink)}
#a2a-root .rubgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}
@media(max-width:760px){#a2a-root .rubgrid{grid-template-columns:1fr}}
#a2a-root .rcard{border:1px solid var(--border);border-left:4px solid var(--det);border-radius:12px;padding:15px 17px;background:#fcfcfe}
#a2a-root .rcard.hyb{border-left-color:var(--hyb)}
#a2a-root .rcard .rt{display:flex;align-items:center;gap:9px;margin-bottom:5px;flex-wrap:wrap}
#a2a-root .rcard .rt h4{margin:0;font-size:15px;color:var(--ink)}
#a2a-root .kpill{font-size:10px;font-weight:800;letter-spacing:.03em;padding:2px 7px;border-radius:5px}
#a2a-root .kpill.det{background:#e7ecf3;color:#5b6472} #a2a-root .kpill.hyb{background:#eae7fb;color:#5a4bc4}
#a2a-root .rcard .desc{font-size:12.5px;color:var(--muted);margin:2px 0 12px}
#a2a-root .segbar{display:flex;height:10px;border-radius:6px;overflow:hidden;margin:4px 0 11px;gap:2px}
#a2a-root .segbar span{height:100%}
#a2a-root .parts{display:flex;flex-wrap:wrap;gap:7px}
#a2a-root .part{font-size:11.5px;background:#eef1f6;border-radius:7px;padding:3px 9px;color:var(--body);display:inline-flex;align-items:center}
#a2a-root .part .pw{font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums;margin-right:6px}
#a2a-root .part.judge{background:#eae7fb;color:#5a4bc4} #a2a-root .part.judge .pw{color:#5a4bc4}
#a2a-root .part .jb{font-size:9px;font-weight:800;color:#fff;background:#8a76e0;border-radius:4px;padding:0 4px;margin-left:6px;letter-spacing:.03em}
#a2a-root .ruleitem{display:flex;align-items:center;gap:9px;font-size:12.5px;color:var(--body);padding:5px 0;border-bottom:1px dashed var(--border-soft)}
#a2a-root .ruleitem:last-of-type{border-bottom:none}
#a2a-root .rv{font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums;background:#eef1f6;border-radius:5px;padding:1px 7px;min-width:34px;text-align:center}
#a2a-root .cnote{font-size:11px;color:var(--muted);margin-top:8px;font-style:italic}
#a2a-root .wmini{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px;padding-top:11px;border-top:1px solid var(--border-soft)}
#a2a-root .wmini .wc{font-size:10.5px;color:var(--body);background:#eef1f6;border-radius:6px;padding:2px 8px;font-variant-numeric:tabular-nums}
#a2a-root .wmini .wc b{color:var(--ink)}
#a2a-root .vtable{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
#a2a-root .vtable th,#a2a-root .vtable td{padding:9px 10px;text-align:center;border-bottom:1px solid var(--border-soft)}
#a2a-root .vtable th:first-child,#a2a-root .vtable td:first-child{text-align:left;font-weight:600;color:var(--ink)}
#a2a-root .vtable th{font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:700}
#a2a-root .vtable td.w{font-variant-numeric:tabular-nums;font-weight:700;color:var(--ink)}
#a2a-root .vtable td.z{color:var(--faint)}
#a2a-root .vtable tr.sum td{font-weight:800;color:var(--blue-ink);border-top:2px solid var(--border)}
"""
