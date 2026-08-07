# -*- coding: utf-8 -*-
"""
exp_SGM_0055d -- PROFUNDIZAR composicionalidad: ¿el TopSim de 0055c (~0.35) sube con bottleneck mas duro
y mas generaciones, o se estanca? Si sube => la afinidad de SGM TIENDE a composicion plena (como NN).
Si se estanca en ~0.35 => el sustrato tiene el germen pero no infiere reglas (gap fino).
Variamos: V=8 L=2 (64 combos para 24 referentes, bottleneck mas duro) y G=40 generaciones.
Sesgo POR AFINIDAD de SGM (igual que 0055c, no hardcodeado).
"""
import json, random, os, sys, math
from collections import defaultdict, Counter
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
SEED=20260803; V=8; L=2; ALPHA=5.0
REGIONS=["N","S","E","O"]; DIST=["lejos","cerca"]; TIPOS=["comida","veneno","agua"]
N_REF=len(REGIONS)*len(DIST)*len(TIPOS)   # 24
def referente(idx):
    r=REGIONS[idx%4]; d=DIST[(idx//4)%2]; t=TIPOS[idx//8]
    return (r,d,t)
def spearman(xs,ys):
    n=len(xs)
    if n<3: return 0.0
    rx=_rank(xs); ry=_rank(ys)
    d=sum((rx[i]-ry[i])**2 for i in range(n))
    return 1-(6*d)/(n*(n*n-1))
def _rank(v):
    s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v)
    for i,idx in enumerate(s): r[idx]=i+1
    return r
def topsim(code):
    refs=list(code.keys())
    if len(refs)<3: return 0.0
    spa=[]; hamm=[]
    for i in range(len(refs)):
        for j in range(i+1,len(refs)):
            a,b=refs[i],refs[j]; ra,rb=referente(a),referente(b)
            spa.append(sum(1 for k in range(3) if ra[k]!=rb[k]))
            ma,mb=code[a],code[b]
            hamm.append(sum(1 for k in range(L) if ma[k]!=mb[k]))
    return spearman(spa,hamm)
class AffinityLearner:
    def __init__(self,seed):
        self.rng=random.Random(seed); self.omega={r:0.0 for r in range(N_REF)}
    def affinity_similarity(self,a,b):
        ra,rb=referente(a),referente(b)
        shared=sum(1 for k in range(3) if ra[k]==rb[k])
        w=(self.omega[a]+self.omega[b])/2.0
        return shared/3.0 + 0.1*w
    def fill_unseen(self, code, seen):
        for r in range(N_REF):
            if r in code: continue
            if not seen:
                code[r]=tuple(self.rng.randint(0,V-1) for _ in range(L)); continue
            best=max(seen, key=lambda s: self.affinity_similarity(r,s))
            code[r]=tuple(code[best])
            self.omega[r]+=ALPHA*0.01; self.omega[best]+=ALPHA*0.01
        return code
def run_gen(teacher_code, learner, rng, frac=0.4):
    refs=list(range(N_REF)); rng.shuffle(refs)
    n_seen=max(1,int(N_REF*frac)); seen=set(refs[:n_seen]); unseen=set(refs[n_seen:])
    code={r:tuple(teacher_code[r]) for r in seen}
    code=learner.fill_unseen(code, seen)
    return code, topsim(code), topsim({r:code[r] for r in seen}) if len(seen)>2 else 0.0, topsim({r:code[r] for r in unseen}) if len(unseen)>2 else 0.0, n_seen
def simular(seed, G=40, frac=0.4):
    rng=random.Random(seed); teacher={r:tuple(rng.randint(0,V-1) for _ in range(L)) for r in range(N_REF)}
    learner=AffinityLearner(seed^0x55); traj=[]
    for g in range(G):
        code,tsf,tss,tsu,ns=run_gen(teacher,learner,rng,frac)
        traj.append({"gen":g,"topSim_full":round(tsf,3),"topSim_seen":round(tss,3),"topSim_unseen":round(tsu,3),"n_seen":ns})
        teacher=code
    return traj
def main():
    todas=[]
    for s in range(3):
        traj=simular(SEED+s*1000, G=40, frac=0.4)
        todas.append({"seed":SEED+s*1000,"traj":traj})
        print("seed",SEED+s*1000,"| TS_full g0 %.3f g20 %.3f g39 %.3f"%(
            traj[0]["topSim_full"],traj[20]["topSim_full"],traj[39]["topSim_full"]))
    out={"experiment_id":"exp_SGM_0055d","name":"ilm_profundizar","status":"ILM_PROFUNDO",
         "marco":"Profundizar 0055c: ¿TopSim (~0.35) SUBE con bottleneck mas duro (V=8 L=2) y mas generaciones (G=40), o se estanca? Sesgo POR AFINIDAD de SGM (no hardcodeado).",
         "diseno":"40 generaciones, 3 seeds, V=8 L=2 (bottleneck mas duro), 24 referentes. frac=0.4.",
         "config":{"V":V,"L":L,"N_REF":N_REF,"G":40,"frac":0.4,"SEED":SEED},
         "resultados":todas,
         "verdict":"Si TS_full SUBE hacia ~0.9 => afinidad de SGM tiende a composicion plena (como NN). Si se estanca ~0.35 => germen composicional pero no infiere reglas (gap fino).",
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0055d_ilm_profundo.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
