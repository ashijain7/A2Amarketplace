import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, json, os, shutil

ROOT="/Users/ashi.jain/Documents/project_deal/results/paper_runs"
OUT="/Users/ashi.jain/Documents/project_deal/A2A_COLM_2026/figures/draft_graphs"
os.makedirs(OUT,exist_ok=True)

CFG=[("C1_sonnet_vs_sonnet","Sonnet 4.5\n(vs Sonnet 4.5)"),
     ("C4_sonnet_vs_gemini","Sonnet 4.5\n(vs Gemini 3.1 Pro Preview)"),
     ("C6_opus_vs_gemini","Opus 4.7\n(vs Gemini 3.1 Pro Preview)"),
     ("C7_gemini_vs_gpt55","Gemini 3.1 Pro Preview\n(vs GPT-5.5)"),
     ("C8_gemini35_vs_gpt55","Gemini 3.5 Flash\n(vs GPT-5.5)"),
     ("C9_opus48_vs_gpt55","Opus 4.8\n(vs GPT-5.5)"),
     ("C10_gpt55_vs_opus48","GPT-5.5\n(vs Opus 4.8)")]
def agg(cfg,ph): return json.load(open(f"{ROOT}/{cfg}/{ph}/aggregate.json"))
def meanreward(cfg,ph): return agg(cfg,ph)["mean_reward"]
def mean_rs(cfg,ph,rub,field):
    a=agg(cfg,ph); xs=[pr["rubric_scores"][rub][field] for pr in a["per_rollout"] if pr["rubric_scores"].get(rub) and pr["rubric_scores"][rub].get(field) is not None]
    return sum(xs)/len(xs) if xs else 0.0


def ti_excl_method(cfg):
    a=agg(cfg,"phase4"); vals=[]
    for pr in a["per_rollout"]:
        t=pr.get("transactional_integrity")
        ar=(t or {}).get("areas") or {}
        sub=[v for k,v in ar.items() if k!="method" and v is not None]
        if sub: vals.append(sum(sub)/len(sub))
    return sum(vals)/len(vals) if vals else 0.0

names=[c[1] for c in CFG]; flat=[n.replace("\n"," ") for n in names]
reward=np.array([[meanreward(c,p) for p in ("phase1","phase2","phase4","phase3")] for c,_ in CFG])
mwr=[mean_rs(c,"phase3","swap_quality","mutual_win_rate") for c,_ in CFG]
ti =[ti_excl_method(c) for c,_ in CFG]
ru2=[mean_rs(c,"phase2","review_utilization","combined") for c,_ in CFG]
ru4=[mean_rs(c,"phase3","review_utilization","combined") for c,_ in CFG]
sm1=[mean_rs(c,"phase1","capability_asymmetry","focal_value_extracted") for c,_ in CFG]
sm2=[mean_rs(c,"phase2","capability_asymmetry","focal_value_extracted") for c,_ in CFG]
cr1=[mean_rs(c,"phase1","deal_outcomes","normalized_closure_rate") for c,_ in CFG]
pe1=[mean_rs(c,"phase1","deal_outcomes","pareto_efficiency") for c,_ in CFG]

print("=== EXTRACTED (current data) ===")
print(f"{'config':32s} I    II   III  IV    MWR  TI   RU2  RU4  SM1  SM2  CR1  PE1")
for i,(c,_) in enumerate(CFG):
    r=reward[i]
    print(f"{flat[i]:32s} {r[0]:.2f} {r[1]:.2f} {r[2]:.2f} {r[3]:.2f}  {mwr[i]:.2f} {ti[i]:.2f} {ru2[i]:.2f} {ru4[i]:.2f} {sm1[i]:4.1f} {sm2[i]:4.1f} {cr1[i]:.2f} {pe1[i]:.2f}")

stages=["Stage I\n(trading)","Stage II\n(reviews)","Stage III\n(payment)","Stage IV\n(SwapShop)"]; ss=["I","II","III","IV"]

# A heatmap
fig,ax=plt.subplots(figsize=(8,5)); im=ax.imshow(reward,cmap="RdYlGn",vmin=0.28,vmax=0.66,aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels(stages,fontsize=9); ax.set_yticks(range(7)); ax.set_yticklabels(names,fontsize=8)
for i in range(7):
    for j in range(4): ax.text(j,i,f"{reward[i,j]:.2f}",ha="center",va="center",fontsize=9)
ax.set_title("Behavioural shift from Stage I to Stage IV  (green = better)",fontsize=11,weight="bold")
fig.colorbar(im,label="score"); fig.tight_layout(); fig.savefig(f"{OUT}/draft_A_heatmap.png",dpi=130); plt.close(fig)

# B small multiples
fig,axs=plt.subplots(2,4,figsize=(12,5.2),sharey=True)
for i in range(7):
    a=axs.flat[i]; a.plot(range(4),reward[i],marker="o",color="#1f4e79",lw=2); a.set_title(names[i],fontsize=8)
    a.set_ylim(0.28,0.66); a.set_xticks(range(4)); a.set_xticklabels(ss,fontsize=8); a.grid(alpha=.3)
axs.flat[-1].axis("off"); fig.suptitle("One mini-chart per model  (same scale)",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/draft_B_smallmultiples.png",dpi=130); plt.close(fig)

# C slope
fig,ax=plt.subplots(figsize=(7.5,5.5))
for i in range(7):
    y0,y3=reward[i,0],reward[i,3]; col="#2c7d2c" if y3>=y0 else "#c23b3b"
    ax.plot([0,1],[y0,y3],marker="o",color=col,lw=2); ax.text(-0.03,y0,flat[i],ha="right",va="center",fontsize=7.5); ax.text(1.03,y3,f"{y3:.2f}",ha="left",va="center",fontsize=8)
ax.set_xticks([0,1]); ax.set_xticklabels(["Stage I\n(trading)","Stage IV\n(SwapShop)"]); ax.set_xlim(-1.0,1.5)
ax.set_ylabel("score"); ax.set_title("Start vs end  (green = rises, red = falls)",fontsize=11,weight="bold"); ax.grid(axis="y",alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_C_slope.png",dpi=130); plt.close(fig)

# D grouped bars
fig,ax=plt.subplots(figsize=(11,5.6)); x=np.arange(7); w=0.2; cols=["#9ecae1","#4292c6","#08519c","#f16913"]
for j in range(4): ax.bar(x+(j-1.5)*w,reward[:,j],w,label=stages[j].replace("\n"," "),color=cols[j])
ax.set_xticks(x); ax.set_xticklabels(flat,fontsize=8,rotation=40,ha="right"); ax.set_ylabel("score")
ax.set_title("Each model's four stages side by side",fontsize=11,weight="bold"); ax.legend(fontsize=8); ax.grid(axis="y",alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_D_groupedbars.png",dpi=130); plt.close(fig)

# E change bars
fig,ax=plt.subplots(figsize=(8,4.6))
d=sorted([(flat[i],reward[i,3]-reward[i,0]) for i in range(7)],key=lambda t:t[1])
lab=[t[0] for t in d]; ch=[t[1] for t in d]
ax.barh(range(7),ch,color=["#c23b3b" if v<0 else "#2c7d2c" for v in ch]); ax.set_yticks(range(7)); ax.set_yticklabels(lab,fontsize=8); ax.axvline(0,color="k",lw=.8)
for i,v in enumerate(ch): ax.text(v+(0.005 if v>=0 else -0.005),i,f"{v:+.2f}",va="center",ha="left" if v>=0 else "right",fontsize=8)
ax.set_xlabel("change in score, Stage I -> Stage IV"); ax.set_title("Net change into barter  (green up, red down)",fontsize=11,weight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/draft_E_changebars.png",dpi=130); plt.close(fig)

# F lines
fig,ax=plt.subplots(figsize=(8.5,5))
for i in range(7): ax.plot(range(4),reward[i],marker="o",lw=2,label=flat[i])
ax.set_xticks(range(4)); ax.set_xticklabels(stages,fontsize=9); ax.set_ylim(0.28,0.66); ax.set_ylabel("score")
ax.set_title("All models as lines",fontsize=11,weight="bold"); ax.legend(fontsize=7.5,ncol=2,loc="lower left"); ax.grid(axis="y",alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_F_lines.png",dpi=130); plt.close(fig)
shutil.copy(f"{OUT}/draft_F_lines.png",f"{OUT}/draft_trajectory.png")

def hbar(vals,fname,title,xlabel,vmax,fmt="{:.2f}",lo=0.0):
    order=sorted(range(7),key=lambda i:vals[i]); lab=[flat[i] for i in order]; v=[vals[i] for i in order]
    cmap=plt.cm.RdYlGn; cols=[cmap((x-lo)/(vmax-lo)) for x in v]
    fig,ax=plt.subplots(figsize=(8,4.4)); ax.barh(range(7),v,color=cols,edgecolor="#444",linewidth=.4)
    ax.set_yticks(range(7)); ax.set_yticklabels(lab,fontsize=8.5); ax.set_xlim(lo,vmax); ax.set_xlabel(xlabel,fontsize=10)
    for i,x in enumerate(v): ax.text(x,i,"  "+fmt.format(x),va="center",fontsize=9)
    ax.set_title(title,fontsize=11,weight="bold"); ax.grid(axis="x",alpha=.3); fig.tight_layout(); fig.savefig(f"{OUT}/{fname}",dpi=130); plt.close(fig)

def gbar(s1,s2,l1,l2,fname,title,ylabel,ymax,fmt="{:.2f}"):
    x=np.arange(7); w=0.38; fig,ax=plt.subplots(figsize=(11,5.6))
    ax.bar(x-w/2,s1,w,label=l1,color="#4292c6"); ax.bar(x+w/2,s2,w,label=l2,color="#f16913")
    ax.set_xticks(x); ax.set_xticklabels(flat,fontsize=8,rotation=40,ha="right"); ax.set_ylabel(ylabel,fontsize=10); ax.set_ylim(0,ymax)
    ax.set_title(title,fontsize=11,weight="bold"); ax.legend(fontsize=9); ax.grid(axis="y",alpha=.3); fig.tight_layout(); fig.savefig(f"{OUT}/{fname}",dpi=130); plt.close(fig)

hbar(mwr,"draft_G_mutualwin.png","Mutual-win rate in SwapShop  (both sides gain)","fraction of swaps that were win-win",1.0)
hbar(ti,"draft_H_settlement_safety.png","Settlement safety under a scammer","transactional-integrity score (excl. smart-method)",1.0,lo=0.75)
gbar(ru2,ru4,"Stage II (reviews)","Stage IV (SwapShop)","draft_I_review_util.png","Review utilization — did it check reviews first?","review-utilization score",1.0)
gbar(sm1,sm2,"Stage I (trading)","Stage II (reviews)","draft_J_value_captured.png","Value captured ($) — extra value the model squeezed out","surplus margin ($)",30,fmt="{:.0f}")

# K scatter
fig,ax=plt.subplots(figsize=(8,6)); ax.scatter(cr1,pe1,s=90,color="#08519c",zorder=3)
offs=[(6,4),(6,-11),(6,4),(6,4),(6,4),(-6,9),(6,-11)]
for i in range(7):
    dx,dy=offs[i]; ax.annotate(flat[i],(cr1[i],pe1[i]),textcoords="offset points",xytext=(dx,dy),ha="left" if dx>0 else "right",fontsize=7.5)
ax.set_xlabel("Closure rate  (fraction of deals closed)",fontsize=10); ax.set_ylabel("Pareto efficiency  (deals good for BOTH sides)",fontsize=10)
ax.set_xlim(0.45,0.95); ax.set_ylim(0,0.9); ax.set_title("Closing deals vs. making good deals  (Stage I)",fontsize=11,weight="bold"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_K_closure_vs_pareto.png",dpi=130); plt.close(fig)
print("\nregenerated all graphs from current data")
