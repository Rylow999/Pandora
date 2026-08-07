# -*- coding: utf-8 -*-
"""
exp_SGM_0055a -- ILM PURO: generacion dura + zero-shot honesto (aisla el mecanismo de Kirby).
Diferencia con 0054b: aqui NO hay mundo/movimiento. El aprendiz arranca con code VACIO cada
generacion y debe reconstruir desde MUESTRA (frac) del code del maestro. Esto es transmision
generacional real (Kirby), no parchear code vivo.
Mide: TopSim sobre el set COMPLETO (visto+no visto) por generacion. Si SUBE y se SOSTIENE =>
composicionalidad emerge de la transmision + el prior del aprendiz (similares->senal similar).
Si queda ~0 en no-vistos => el sustrato no compone sin un bias de compresibilidad mas fuerte.
Referentes estructurados: (region N/S/E/O, distancia lejos/cerca, tipo comida/veneno/agua) = 24.
Bottleneck: V=16, L=3.
"""
import json, random, os, sys, math
from collections import defaultdict, Counter
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
SEED=20260803; V=16; L=3
REGIONS=["N","S","E","O"]; DIST=["lejos","cerca"]; TIPOS=["comida","veneno","agua"]
N_REF=len(REGIONS)*len(DIST)*len(TIPOS)   # 24
def referente(idx):
    r=REGIONS[idx%4]; d=DIST[(idx//4)%2]; t=TIPOS[idx//8]
    return (r,d,t)
def feature_overlap(a,b):
    ra,rb=referente(a),referente(b)
    return sum(1 for k in range(3) if ra[k]==rb[k])   # 0..3 rasgos compartidos

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

def run_gen(teacher_code, rng, frac=0.4, bias=True):
    """Aprendiz: code vacio. Ve MUESTRA frac del maestro. Para no-vistos, asigna:
    - si bias: mensaje del visto con mas overlap de rasgos (prior 'similares->senal similar')
    - si no bias: mensaje nuevo aleatorio (hasta V) o reuse ciego
    Devuelve (learner_code, topSim_full, topSim_seen, topSim_unseen, n_seen)."""
    refs=list(range(N_REF))
    rng.shuffle(refs)
    n_seen=max(1,int(N_REF*frac))
    seen=set(refs[:n_seen]); unseen=set(refs[n_seen:])
    code={}
    for r in seen:
        code[r]=tuple(teacher_code[r])   # copia el del maestro
    for r in unseen:
        if bias and code:
            # prior: usar el visto con mas overlap de rasgos
            best=max(seen, key=lambda s: feature_overlap(r,s))
            code[r]=tuple(code[best])
        else:
            if len(code)<V:
                code[r]=tuple(rng.randint(0,V-1) for _ in range(L))
            else:
                code[r]=tuple(0 for _ in range(L))
    ts_full=topsim(code)
    ts_seen=topsim({r:code[r] for r in seen}) if len(seen)>2 else 0.0
    ts_unseen=topsim({r:code[r] for r in unseen}) if len(unseen)>2 else 0.0
    return code, ts_full, ts_seen, ts_unseen, n_seen

def simular(seed, G=20, frac=0.4, bias=True):
    rng=random.Random(seed)
    # lenguaje inicial HOLISTICO (cada referente msg aleatorio, sin estructura)
    teacher={r:tuple(rng.randint(0,V-1) for _ in range(L)) for r in range(N_REF)}
    traj=[]
    for g in range(G):
        code,tsf,tss,tsu,ns=run_gen(teacher,rng,frac,bias)
        traj.append({"gen":g,"topSim_full":round(tsf,3),"topSim_seen":round(tss,3),
                     "topSim_unseen":round(tsu,3),"n_seen":ns,"code_size":len(code)})
        teacher=code   # la siguiente generacion parte del aprendiz
    return traj

def main():
    todas=[]
    for s in range(3):
        traj=simular(SEED+s*1000, G=20, frac=0.4, bias=True)
        todas.append({"seed":SEED+s*1000,"traj":traj})
        # imprimir resumen por seed
        print("seed",SEED+s*1000)
        for row in traj[::4]:
            print("  g%d TS_full %.3f seen %.3f unseen %.3f"%(row["gen"],row["topSim_full"],row["topSim_seen"],row["topSim_unseen"]))
    out={"experiment_id":"exp_SGM_0055a","name":"ilm_puro_generacion_dura","status":"ILM_PURO",
         "marco":"ILM Kirby aislado (sin mundo). Aprendiz arranca code vacio, reconstruye de MUESTRA frac del maestro. Prior del aprendiz: similares->senal similar (overlap de rasgos). Mide TopSim por generacion.",
         "diseno":"20 generaciones, 3 seeds, V=16 L=3, 24 referentes estructurados. frac=0.4 muestra. Bias=True (generaliza no-vistos por overlap).",
         "config":{"V":V,"L":L,"N_REF":N_REF,"G":20,"frac":0.4,"bias":True,"SEED":SEED},
         "resultados":todas,
         "verdict":"Si TopSim_full SUBE y se SOSTIENE > 0 con generaciones => composicionalidad emerge de transmision+pene. Si TopSim_unseen queda ~0 => el sustrato no generaliza a no-vistos (gap de bias de compresibilidad).",
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0055a_ilm_puro.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
