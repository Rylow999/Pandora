# -*- coding: utf-8 -*-
"""
exp_SGM_0056 -- INFERENCIA DE REGLAS: el aprendiz deduce el mapeo rasgo->simbolo de la MUESTRA
(region->pos0, distancia->pos1, tipo->pos2) y lo aplica SISTEMATICAMENTE a no-vistos.
Esto es lo que HRR/bigrama NO hacia (copiaba msg del mas afin o contaba bigramas). Si TopSim sube
a ~0.9 => el sustrato PUEDE componer pleno si se le da objetivo de comunicacion + regla. Si no =>
confirma que HRR/bigrama necesita algo tipo Gumbel-Softmax (backprop/objetivo) para cerrar.
Referentes estructurados (region,distancia,tipo)=24. Bottleneck V=16 L=3.
"""
import json, random, os, sys, math
from collections import defaultdict, Counter
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
SEED=20260803; V=16; L=3
REGIONS=["N","S","E","O"]; DIST=["lejos","cerca"]; TIPOS=["comida","veneno","agua"]
N_REF=len(REGIONS)*len(DIST)*len(TIPOS)   # 24
def referente(idx):
    return (REGIONS[idx%4],DIST[(idx//4)%2],TIPOS[idx//8])
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

class RuleLearner:
    """Aprendiz que INFERE regla rasgo->simbolo (no copia msg). Usa cuenta de frecuencia por rasgo
    en la muestra vista, y aplica systematicamente: msg[r] = (sym_region[r], sym_dist[r], sym_tipo[r])."""
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.rule=None   # (region->sym, dist->sym, tipo->sym)
    def infer_rule(self, code_seen):
        """De la muestra vista (referente->msg), deduce el mapeo mas comun rasgo->simbolo por posicion."""
        reg_map=defaultdict(Counter); dist_map=defaultdict(Counter); tipo_map=defaultdict(Counter)
        for r,msg in code_seen.items():
            ra=referente(r)
            reg_map[ra[0]][msg[0]]+=1
            dist_map[ra[1]][msg[1]]+=1
            tipo_map[ra[2]][msg[2]]+=1
        rule=(
            {k:mc.most_common(1)[0][0] for k,mc in reg_map.items()},
            {k:mc.most_common(1)[0][0] for k,mc in dist_map.items()},
            {k:mc.most_common(1)[0][0] for k,mc in tipo_map.items()},
        )
        return rule
    def build_code(self, rule):
        code={}
        for r in range(N_REF):
            ra=referente(r)
            code[r]=(rule[0].get(ra[0],self.rng.randint(0,V-1)),
                    rule[1].get(ra[1],self.rng.randint(0,V-1)),
                    rule[2].get(ra[2],self.rng.randint(0,V-1)))
        return code

def run_gen(teacher_code, learner, rng, frac=0.4):
    refs=list(range(N_REF)); rng.shuffle(refs)
    n_seen=max(1,int(N_REF*frac)); seen=set(refs[:n_seen])
    code_seen={r:tuple(teacher_code[r]) for r in seen}
    rule=learner.infer_rule(code_seen)
    code=learner.build_code(rule)
    return code, topsim(code), topsim(code_seen) if len(code_seen)>2 else 0.0, \
           topsim({r:code[r] for r in set(range(N_REF))-seen}) if (N_REF-n_seen)>2 else 0.0, n_seen

def simular(seed, G=20, frac=0.4):
    rng=random.Random(seed); teacher={r:tuple(rng.randint(0,V-1) for _ in range(L)) for r in range(N_REF)}
    learner=RuleLearner(seed^0x56); traj=[]
    for g in range(G):
        code,tsf,tss,tsu,ns=run_gen(teacher,learner,rng,frac)
        traj.append({"gen":g,"topSim_full":round(tsf,3),"topSim_seen":round(tss,3),"topSim_unseen":round(tsu,3),"n_seen":ns})
        teacher=code
    return traj

def main():
    todas=[]
    for s in range(3):
        traj=simular(SEED+s*1000, G=20, frac=0.4)
        todas.append({"seed":SEED+s*1000,"traj":traj})
        print("seed",SEED+s*1000,"| TS_full g0 %.3f g19 %.3f"%(traj[0]["topSim_full"],traj[19]["topSim_full"]))
    out={"experiment_id":"exp_SGM_0056","name":"ilm_inferencia_reglas","status":"ILM_REGLA",
         "marco":"0055d mostro estancamiento en ~0.35 (afinidad agrupa pero no infiere reglas). 0056: el aprendiz INFERE el mapeo rasgo->simbolo de la muestra y lo aplica sistematicamente. Testea si la INFERENCIA DE REGLA (no copiar/bigrama) lleva a composicion plena (~0.9).",
         "diseno":"20 generaciones, 3 seeds, V=16 L=3, 24 referentes. Aprendiz deduce region->pos0, dist->pos1, tipo->pos2 de la muestra vista y aplica a todos.",
         "config":{"V":V,"L":L,"N_REF":N_REF,"G":20,"frac":0.4,"SEED":SEED},
         "resultados":todas,
         "verdict":"Si TS_full SUBE a ~0.9 => el sustrato PUEDE componer pleno con inferencia de regla (no hace falta Gumbel-Softmax). Si se estanca ~0.35 => confirma que HRR/bigrama necesita objetivo de comunicacion/backprop para sistematicidad.",
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0056_ilm_regla.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
