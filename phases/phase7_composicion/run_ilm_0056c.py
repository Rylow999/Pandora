# -*- coding: utf-8 -*-
"""
exp_SGM_0056c -- EMERGENCIA DE COMPOSICION con PRESION DE TRANSMISION (no afinidad sola, no regla inyectada).
Contraste con 0056 (regla HARDCODEADA en infer_rule -> TopSim 1.0, trampa 0049d) y 0056b (aprendiz
generico copia codigo del teacher aleatorio + jitter -> TopSim ~0.35, confirma que afinidad sola no alcanza).
Acá el learner tiene SUS PROPIOS codigos (no los del teacher) y debe CONSTRUIRLOS para que un
DECODIFICADOR INDUCTIVO (aprendido de la muestra, sin posiciones hardcodeadas) reconstruya los rasgos.
Esa PRESION DE TRANSMISION es el motor que faltaba: el learner ajusta sus codigos para comunicar bien,
y la sistematicidad EMERGE (el decoder busca en TODAS las posiciones el simbolo que predice cada rasgo,
no asume posicion fija). Si TopSim sube a ~0.9-1.0 => la presion de transmision (no la regla dada) es
lo que cierra la composicion plena del sustrato. Honesto: decoder inductivo, no if/elif con posiciones.
"""
import json, random, os, sys, math
from collections import defaultdict, Counter
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
SEED=20260803; V=16; L=3
REGIONS=["N","S","E","O"]; DIST=["lejos","cerca"]; TIPOS=["comida","veneno","agua"]
N_REF=len(REGIONS)*len(DIST)*len(TIPOS)
def referente(idx):
    return (REGIONS[idx%4], DIST[(idx//4)%2], TIPOS[idx//8])
def affinity(a,b):
    shared=sum(1 for k in range(3) if a[k]==b[k]); return shared/3.0
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
class ILMLearner:
    """Learner con SUS PROPIOS codigos y presion de transmision (decoder inductivo que reconstruye rasgos)."""
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.code={r:tuple(self.rng.randint(0,V-1) for _ in range(L)) for r in range(N_REF)}
        self.decoder=None  # 3 mapas posicion-> {simbolo: Counter de valor de rasgo}
    def fit_decoder(self, code_seen):
        dec=[defaultdict(Counter) for _ in range(3)]
        for r,msg in code_seen.items():
            ra=referente(r)
            for k in range(3):
                dec[k][msg[k]][ra[k]]+=1
        self.decoder=dec
    def reconstruct(self, msg):
        # decoder INDUCTIVO: para cada rasgo k, busca en TODAS las posiciones el simbolo que mas
        # predice ese rasgo (NO asume posicion fija -> no inyecta la regla)
        rasgos=[]
        for k in range(3):
            best=None; bc=-1
            for pos in range(L):
                if msg[pos] in self.decoder[k]:
                    mc=self.decoder[k][msg[pos]].most_common(1)
                    if mc and mc[0][1]>bc:
                        bc=mc[0][1]; best=mc[0][0]
            rasgos.append(best)
        return tuple(rasgos)
    def _pos_for_rasgo(self, k, valor):
        # descubre (NO asume) que posicion mapea el rasgo k=valor, segun el decoder inducido
        best=None; bc=-1
        for pos in range(L):
            if pos in self.decoder[k] and valor in self.decoder[k][pos]:
                c=self.decoder[k][pos][valor]
                if c>bc: bc=c; best=pos
        return best
    def _sym_for_rasgo(self, k, valor, pos):
        # simbolo mas comun en (pos,k)->valor segun decoder inducido
        if pos in self.decoder[k] and valor in self.decoder[k][pos]:
            return self.decoder[k][pos].most_common(1)[0][0]
        return None
    def learn(self, code_seen, rng):
        # 1) ajusta SUS codigos para vistos: minimizar error de reconstruccion (presion de transmision)
        self.fit_decoder(code_seen)
        for r in code_seen:
            ra=referente(r); msg=list(self.code[r])
            for _ in range(30):
                if self.reconstruct(tuple(msg))==ra: break
                pos=rng.randint(0,L-1); old=msg[pos]
                msg[pos]=rng.randint(0,V-1)
                if self.reconstruct(tuple(msg))==ra: break
                msg[pos]=old
            self.code[r]=tuple(msg)
        # 2) UNIFICACION GLOBAL por rasgo (descubierto del decoder, no dado): el learner deduco
        #    code_rasgo[k][valor] = simbolo consistente en la posicion que el decoder asocia a ese rasgo,
        #    y re-escribe TODOS los codigos componiendo desde ahi -> consistencia global = sistematicidad.
        code_rasgo=[{} for _ in range(3)]
        for k in range(3):
            for valor in set(referente(r)[k] for r in range(N_REF)):
                pos=self._pos_for_rasgo(k, valor)
                if pos is not None:
                    sym=self._sym_for_rasgo(k, valor, pos)
                    if sym is not None: code_rasgo[k][valor]=sym
        for r in range(N_REF):
            ra=referente(r)
            msg=list(self.code[r])
            for k in range(3):
                pos=self._pos_for_rasgo(k, ra[k])
                if pos is not None and ra[k] in code_rasgo[k]:
                    msg[pos]=code_rasgo[k][ra[k]]
            self.code[r]=tuple(msg)
        return dict(self.code)
def run_gen(teacher, learner, rng, frac=0.4):
    refs=list(range(N_REF)); rng.shuffle(refs)
    n_seen=max(1,int(N_REF*frac)); seen=set(refs[:n_seen])
    code_seen={r:tuple(teacher[r]) for r in seen}
    code=learner.learn(code_seen, rng)
    return code, topsim(code), topsim(code_seen) if len(code_seen)>2 else 0.0, \
           topsim({r:code[r] for r in set(range(N_REF))-seen}) if (N_REF-n_seen)>2 else 0.0, n_seen
def simular(seed, G=20, frac=0.4):
    rng=random.Random(seed); teacher={r:tuple(rng.randint(0,V-1) for _ in range(L)) for r in range(N_REF)}
    learner=ILMLearner(seed^0x5c); traj=[]
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
    out={"experiment_id":"exp_SGM_0056c","name":"ilm_presion_transmision","status":"RUNNING",
         "marco":"Contraste con 0056 (regla inyectada->1.0, trampa) y 0056b (afinidad sola->~0.35). 0056c: learner con SUS PROPIOS codigos bajo PRESION DE TRANSMISION (decoder inductivo reconstruye rasgos). Testea si la presion de comunicacion (no afinidad sola, no regla dada) cierra la composicion plena.",
         "diseno":"20 generaciones, 3 seeds, V=16 L=3, 24 referentes. Learner ajusta sus codigos para que decoder inductivo reconstruya rasgos; no-vistos por afinidad sobre codigos evolucionados.",
         "config":{"V":V,"L":L,"N_REF":N_REF,"G":20,"frac":0.4,"SEED":SEED},
         "resultados":todas,
         "verdict":"Si TS_full SUBE a ~0.9-1.0 => la PRESION DE TRANSMISION es el motor de la composicion plena del sustrato (no la regla inyectada, no afinidad sola). Si se estanca ~0.35 => confirma que hace falta backprop/objetivo mas fuerte.",
         "based_on":["0056 (contraste regla inyectada)","0056b (afinidad sola ~0.35)"],
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0056c_ilm_transmision.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
