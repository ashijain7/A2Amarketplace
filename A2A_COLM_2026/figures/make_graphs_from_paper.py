# Build ALL draft graphs from the NUMBERS PRINTED IN THE PAPER tables.
#  - Metric graphs (G-K): read directly from the paper table columns.
#  - Overall-score graphs (A-F): the paper prints no reward, so reward is COMPUTED
#    from the paper's per-dimension cells using the documented rubric weights
#    (renormalised over the dimensions present). Settlement (Stage III) uses the
#    standard five-dimension weighting; transactional integrity is reported
#    separately and not folded into the reward.
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, re

TEX="/Users/ashi.jain/Documents/project_deal/A2A_COLM_2026/agent2agentmarketplace_COLM.tex"
OUT="/Users/ashi.jain/Documents/project_deal/A2A_COLM_2026/figures/draft_graphs"
lines=open(TEX).read().split("\n")
def clean(c):
    c=re.sub(r"\\cellcolor\{[^}]*\}","",c); c=c.replace("$","").replace("*","").replace("\\\\","")
    return c.strip()
def num(s):
    try: return float(s)
    except: return None
def rows_after(sub,start=0):
    hi=next(i for i,l in enumerate(lines) if sub in l and i>=start); out=[]
    for l in lines[hi+1:]:
        if "\\end{tabular}" in l: break
        if "(vs" in l:
            cs=[clean(x) for x in l.split("&")]; out.append((cs[0],cs[1:]))
    return hi,out
_,md=rows_after("& DO & CA & NQ & PP & DO & CA & RU")
_,sw=rows_after("& SQ & DO & CA & RU & PP")
hi1,a1=rows_after("& CR & PE & SP & BS & RTC & nCR & DO & SR & OR & PF & $\\Delta$ & SM & CA & An")
hi2,a2=rows_after("& CR & PE & SP & BS & RTC & nCR & DO & SR & OR & PF & $\\Delta$ & SM & CA & LM",hi1+1)
_,asw=rows_after("& SwC & MWR & FSM & SQ & CR")

flat=[r[0] for r in md]; names=[r.replace(" (vs ","\n(vs ") for r in flat]

# ---- derive per-stage reward from paper dimension cells ----
def wavg(pairs):  # pairs=[(weight,value_or_None)]
    t=w=0.0
    for ww,v in pairs:
        if v is not None: t+=ww*v; w+=ww
    return t/w if w else 0.0
reward=[]
for i in range(7):
    m=[num(x) for x in md[i][1]]; s=[num(x) for x in sw[i][1]]
    rI  =wavg([(0.325,m[0]),(0.275,m[1]),(0.225,m[2]),(0.175,m[3])])
    rII =wavg([(0.25,m[4]),(0.20,m[5]),(0.20,m[7]),(0.15,m[8]),(0.20,m[6])])
    rIII=wavg([(0.25,m[9]),(0.20,m[10]),(0.20,m[12]),(0.15,m[13]),(0.20,m[11])])  # std 5 dims, no TI
    rIV =wavg([(0.10,s[1]),(0.15,s[2]),(0.10,s[4]),(0.20,s[3]),(0.30,s[0])])      # DO,CA,PP,RU,SQ
    reward.append([rI,rII,rIII,rIV])
reward=np.array(reward)

stages=["Stage I\n(trading)","Stage II\n(reviews)","Stage III\n(payment)","Stage IV\n(SwapShop)"]; ss=["I","II","III","IV"]
lo,hi=reward.min()-0.03, reward.max()+0.03

# A heatmap
fig,ax=plt.subplots(figsize=(8,5)); im=ax.imshow(reward,cmap="RdYlGn",vmin=lo,vmax=hi,aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels(stages,fontsize=9); ax.set_yticks(range(7)); ax.set_yticklabels(names,fontsize=8)
for i in range(7):
    for j in range(4): ax.text(j,i,f"{reward[i,j]:.2f}",ha="center",va="center",fontsize=9)
ax.set_title("Behavioural shift from Stage I to Stage IV  (green = better)",fontsize=11,weight="bold")
fig.colorbar(im,label="reward (from paper dimensions)"); fig.tight_layout(); fig.savefig(f"{OUT}/draft_A_heatmap.png",dpi=130); plt.close(fig)
# B small multiples
fig,axs=plt.subplots(2,4,figsize=(12,5.2),sharey=True)
for i in range(7):
    a=axs.flat[i]; a.plot(range(4),reward[i],marker="o",color="#1f4e79",lw=2); a.set_title(names[i],fontsize=8)
    a.set_ylim(lo,hi); a.set_xticks(range(4)); a.set_xticklabels(ss,fontsize=8); a.grid(alpha=.3)
axs.flat[-1].axis("off"); fig.suptitle("One mini-chart per model  (same scale)",fontsize=12,weight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/draft_B_smallmultiples.png",dpi=130); plt.close(fig)
# C slope
fig,ax=plt.subplots(figsize=(7.5,5.5))
for i in range(7):
    y0,y3=reward[i,0],reward[i,3]; col="#2c7d2c" if y3>=y0 else "#c23b3b"
    ax.plot([0,1],[y0,y3],marker="o",color=col,lw=2); ax.text(-0.03,y0,flat[i],ha="right",va="center",fontsize=7.5); ax.text(1.03,y3,f"{y3:.2f}",ha="left",va="center",fontsize=8)
ax.set_xticks([0,1]); ax.set_xticklabels(["Stage I\n(trading)","Stage IV\n(SwapShop)"]); ax.set_xlim(-1.0,1.5)
ax.set_ylabel("reward (from paper dimensions)"); ax.set_title("Start vs end  (green = rises, red = falls)",fontsize=11,weight="bold"); ax.grid(axis="y",alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_C_slope.png",dpi=130); plt.close(fig)
# D grouped bars
fig,ax=plt.subplots(figsize=(11,5.6)); x=np.arange(7); w=0.2; cols=["#9ecae1","#4292c6","#08519c","#f16913"]
for j in range(4): ax.bar(x+(j-1.5)*w,reward[:,j],w,label=stages[j].replace("\n"," "),color=cols[j])
ax.set_xticks(x); ax.set_xticklabels(flat,fontsize=8,rotation=40,ha="right"); ax.set_ylabel("reward (from paper dimensions)")
ax.set_title("Each model's four stages side by side",fontsize=11,weight="bold"); ax.legend(fontsize=8); ax.grid(axis="y",alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_D_groupedbars.png",dpi=130); plt.close(fig)
# E change bars
fig,ax=plt.subplots(figsize=(8,4.6))
d=sorted([(flat[i],reward[i,3]-reward[i,0]) for i in range(7)],key=lambda t:t[1]); lab=[t[0] for t in d]; ch=[t[1] for t in d]
ax.barh(range(7),ch,color=["#c23b3b" if v<0 else "#2c7d2c" for v in ch]); ax.set_yticks(range(7)); ax.set_yticklabels(lab,fontsize=8); ax.axvline(0,color="k",lw=.8)
for i,v in enumerate(ch): ax.text(v+(0.004 if v>=0 else -0.004),i,f"{v:+.2f}",va="center",ha="left" if v>=0 else "right",fontsize=8)
ax.set_xlabel("change in reward, Stage I -> Stage IV"); ax.set_title("Net change into barter  (green up, red down)",fontsize=11,weight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/draft_E_changebars.png",dpi=130); plt.close(fig)
# F lines
fig,ax=plt.subplots(figsize=(8.5,5))
for i in range(7): ax.plot(range(4),reward[i],marker="o",lw=2,label=flat[i])
ax.set_xticks(range(4)); ax.set_xticklabels(stages,fontsize=9); ax.set_ylim(lo,hi); ax.set_ylabel("reward (from paper dimensions)")
ax.set_title("All models as lines",fontsize=11,weight="bold"); ax.legend(fontsize=7.5,ncol=2,loc="lower left"); ax.grid(axis="y",alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_F_lines.png",dpi=130); plt.close(fig)
import shutil; shutil.copy(f"{OUT}/draft_F_lines.png",f"{OUT}/draft_trajectory.png")

# ---- metric graphs G-K (direct paper columns) ----
f=lambda s: float(s)
mwr=[f(asw[i][1][1]) for i in range(7)]; ti=[f(md[i][1][14]) for i in range(7)]
ru2=[f(md[i][1][6]) for i in range(7)]; ru4=[f(sw[i][1][3]) for i in range(7)]
sm1=[f(a1[i][1][11]) for i in range(7)]; sm2=[f(a2[i][1][11]) for i in range(7)]
cr1=[f(a1[i][1][0]) for i in range(7)]; pe1=[f(a1[i][1][1]) for i in range(7)]
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
hbar(ti,"draft_H_settlement_safety.png","Settlement safety under a scammer","transactional-integrity score",1.0,lo=0.75)
gbar(ru2,ru4,"Stage II (reviews)","Stage IV (SwapShop)","draft_I_review_util.png","Review utilization — did it check reviews first?","review-utilization score",1.0)
gbar(sm1,sm2,"Stage I (trading)","Stage II (reviews)","draft_J_value_captured.png","Value captured ($) — extra value the model squeezed out","surplus margin ($)",30,fmt="{:.0f}")
fig,ax=plt.subplots(figsize=(8,6)); ax.scatter(cr1,pe1,s=90,color="#08519c",zorder=3)
offs=[(6,5),(6,-12),(6,5),(6,6),(6,-12),(-6,9),(6,5)]
for i in range(7):
    dx,dy=offs[i]; ax.annotate(flat[i],(cr1[i],pe1[i]),textcoords="offset points",xytext=(dx,dy),ha="left" if dx>0 else "right",fontsize=7.5)
ax.set_xlabel("Closure rate  (fraction of deals closed)",fontsize=10); ax.set_ylabel("Pareto efficiency  (deals good for BOTH sides)",fontsize=10)
ax.set_xlim(0.45,0.95); ax.set_ylim(0,0.9); ax.set_title("Closing deals vs. making good deals  (Stage I)",fontsize=11,weight="bold"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(f"{OUT}/draft_K_closure_vs_pareto.png",dpi=130); plt.close(fig)

print("ALL 12 graphs rebuilt from PAPER numbers (A-F reward = weighted from paper dimensions)")
print(f"{'config':30s}  I    II   III  IV   (derived reward)")
for i in range(7): print(f"{flat[i]:30s} {reward[i,0]:.2f} {reward[i,1]:.2f} {reward[i,2]:.2f} {reward[i,3]:.2f}")

# --- also copy the graphs the paper \includegraphics from the repo root, so the
#     root copies the paper reads are always the updated ones ---
import shutil as _sh
ROOTDIR="/Users/ashi.jain/Documents/project_deal/A2A_COLM_2026"
for _fn in ("draft_B_smallmultiples.png","draft_H_settlement_safety.png",
            "draft_I_review_util.png","draft_J_value_captured.png","draft_K_closure_vs_pareto.png"):
    _sh.copy(f"{OUT}/{_fn}", f"{ROOTDIR}/{_fn}")
print("copied the 5 paper-used graphs to repo root")
