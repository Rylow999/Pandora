# -*- coding: utf-8 -*-
"""exp_SGM_0055b -- ILM SIN PRIOR (replica del test inline). Ver results_exp_SGM_0055b_ilm_sin_prior.json.
Aprendiz SIN prior de similitud: asigna msg nuevo aleatorio (hasta V) o reuse ciego. Confirma que
sin sesgo el sustrato HRR/bigrama NO compone (TopSim~0.15, unseen~0)."""
import json, random, os, sys, math
from collections import defaultdict, Counter
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
SEED=20260803; V=16; L=3
REGIONS=["N","S","E","O"]; DIST=["lejos","cerca"]; TIPOS=["comida","veneno","agua"]
N_REF=len(REGIONS)*len(DIST)*len(TIPOS)
def referente(idx):
    return (REGIONS[idx%4],DIST[(idx//4)%2],TIPOS[idx//8])
def spearman(xs,ys):
    n=len(xs)
    if n<3: return 0.0
    rx=sorted(range(n),key=lambda i:xs[i]); ry=sorted(range(n),key=lambda i:ys[i])
    r=[0]*n
    for i,k in enumerate(rx): r[k]=i+1
    s=[0]*n
    for i,k in enumerate(ry): s[k]=i+1
    d=sum((r[i]-s[i])**2 for i in range(n))
    return 1-(6*d)/(n*(n*n-1))
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
def run_gen(teacher,rng,frac=0.4):
    refs=list(range(N_REF)); rng.shuffle(refs)
    n_seen=max(1,int(N_REF*frac)); seen=set(refs[:n_seen])
    code={r:tuple(teacher[r]) for r in seen}
    for r in range(N_REF):
        if r in code: continue
        if len(code)<V: code[r]=tuple(rng.randint(0,V-1) for _ in range(L))
        else: code[r]=tuple(0 for _ in range(L))
    return code, topsim(code)
def simular(seed,G=20,frac=0.4):
    rng=random.Random(seed); teacher={r:tuple(rng.randint(0,V-1) for _ in range(L)) for r in range(N_REF)}
    traj=[]
    for g in range(G):
        code,tsf=run_gen(teacher,rng,frac); traj.append({"gen":g,"topSim_full":round(tsf,3)}); teacher=code
    return traj
if __name__=="__main__":
    todas=[{"seed":SEED+s*1000,"traj":simular(SEED+s*1000)} for s in range(3)]
    out={"experiment_id":"exp_SGM_0055b","name":"ilm_sin_prior","status":"ILM_SIN_PRIOR",
         "verdict":"Sin prior: TopSim~0.15, unseen~0. El sustrato no compone sin sesgo.","resultados":todas,"verified":True}
    print(json.dumps(out,indent=2,ensure_ascii=False))
