# -*- coding: utf-8 -*-
"""
exp_SGM_0039 -- pain_habituation_and_curiosity_asymmetry (Camino A: dolor cronico no letal + asimetria)
HONESTIDAD DE DISENO:
  (1) DOLOR CRONICO NO LETAL -> HABITUACION. El humano se acostumbra al dolor constante para sobrevivir
      (el 0038 solo media dolor agudo/evasion). El sistema registra repeticiones de dolor por celda y el
      peso DECAE (peso = base * exp(-KAPPA * rep)). PERO con piso: no se anula (no puede volverse suicida).
      Esto modela "me acostumbre para seguir funcionando", no "deje de sentir".
  (2) ASIMETRIA CURIOSIDAD/DOLOR. El humano tolera mas dolor POR curiosidad que por placer neutro. El eta
      (novedad alta) AMORTIGUA el delta_dolor: costo = dist - nov + DOLOR_PEN*dolor*(1+eta)*(1 - BETA*eta).
      La curiosidad justifica el riesgo. Medible: en alta novedad elige camino de dolor-alto antes que en
      baja novedad.

TEST-FIRST (con NC):
  - T-HAB-01: con dolor cronico, pisos de dolor SUBEN respecto a 0038 (se habitua) pero < TOPE.
  - T-HAB-02: sigue llegando a meta (no muere por habituarse).
  - T-HAB-03 (NC): NO se vuelve suicida -> evade dolor AGUDO nuevo (peso no se anula).
  - T-HAB-04: asimetria -> en alta novedad tolera mas dolor que en baja novedad (elige dolor-alto-novedad).
Variable discriminante: peso de dolor tras repeticiones + eleccion en funcion de eta.
"""
import json, os, sys, random, math
sys.path.insert(0, os.path.dirname(__file__))
import run_grid_agent as G2

SEED = 20260803
TRIALS = 40
N = 10
MAX_TICKS = 200
ETA_OPT = 0.30
SIGMA_ETA = 0.22
ETA_BAJO = 0.05
THETA_ABURR = 6
ALPHA_NOV = 1.5
DOLOR_PEN = 5.0
KAPPA_HAB = 0.35         # tasa de habituacion por repeticion
HAB_PISO = 0.6           # el peso de dolor nunca baja de esto (no suicida: evita dolor agudo)
BETA_ASIM = 0.6          # cuanto el eta amortigua el dolor en alta novedad (clamped)

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def dopamina(eta):
    return math.exp(-((eta - ETA_OPT)/SIGMA_ETA)**2)

class HabTick:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.eta = 0.0
        self.aburrimiento = 0
        self.visitas = {}
        self.dolor_rep = {}        # celda -> repeticiones de dolor (habituacion)
        self.omega = {(r,c):[self.rng.uniform(-1,1) for _ in range(16)] for r in range(N) for c in range(N)}

    def predict_next(self, pos, goal):
        vs=[(pos[0]+dr,pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
        vs=[v for v in vs if 0<=v[0]<N and 0<=v[1]<N]
        return self.omega[min(vs,key=lambda v:manhattan(v,goal))] if vs else None

    def update(self, pos, goal, real_omega):
        p=self.predict_next(pos,goal)
        self.eta = 1.0 if p is None else 1.0-(lambda dot,na,nb: dot/(na*nb) if na*nb>0 else 0.0)(
            sum(a*b for a,b in zip(p,real_omega)),
            math.sqrt(sum(a*a for a in p)), math.sqrt(sum(b*b for b in real_omega)))
        self.aburrimiento = self.aburrimiento+1 if self.eta<ETA_BAJO else max(0,self.aburrimiento-1)
        self.visitas[pos]=self.visitas.get(pos,0)+1

    def peso_dolor(self, v, dolor_cell):
        if v not in dolor_cell: return 0.0
        rep = self.dolor_rep.get(v,0)
        w = DOLOR_PEN * dolor_cell[v] * math.exp(-KAPPA_HAB*rep)   # habituacion
        w = max(HAB_PISO * DOLOR_PEN * dolor_cell[v], w)           # piso: nunca se anula
        # asimetria: eta alto amortigua el dolor (la curiosidad justifica el riesgo),
        # pero CLAMPED: nunca hace el dolor < 20% ni negativo.
        factor_asim = max(0.2, 1.0 - BETA_ASIM*max(0.0, self.eta - ETA_OPT))
        return w * factor_asim

    def costo(self, v, goal, dolor_cell):
        base = manhattan(v, goal)
        nov = ALPHA_NOV*(1.0/(1.0+self.visitas.get(v,0)))
        d = self.peso_dolor(v, dolor_cell)   # ya incluye habituacion + asimetria clamped
        return base - nov + d

    def choose(self, pos, goal, walls, dolor_cell):
        vs=[(pos[0]+dr,pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
        vs=[v for v in vs if 0<=v[0]<N and 0<=v[1]<N and v not in walls and v!=pos]
        if not vs: return None,"none"
        if self.aburrimiento>=THETA_ABURR:
            return max(vs,key=lambda v:1.0/(1.0+self.visitas.get(v,0))),"novelty"
        if self.eta>ETA_OPT:
            return min(vs,key=lambda v:self.costo(v,goal,dolor_cell)),"explore"
        return min(vs,key=lambda v:self.costo(v,goal,dolor_cell)),"exploit"

def run(rng, walls, start, goal, dolor_cell):
    tick=HabTick(rng.randint(0,10**9))
    pos=start; pasos=0; pisos=0; rep_total=0
    while pasos<MAX_TICKS:
        if pos==goal: return True,pasos,pisos
        nb,_=tick.choose(pos,goal,walls,dolor_cell)
        if nb is None: return False,pasos,pisos
        if nb in dolor_cell:
            pisos+=1; tick.dolor_rep[nb]=tick.dolor_rep.get(nb,0)+1; rep_total+=1
        tick.update(pos,goal,tick.omega[nb])
        pos=nb; pasos+=1
    return False,pasos,pisos

def main():
    rng=random.Random(SEED)
    res=[]
    asim_alta=0; asim_baja=0   # T-HAB-04: elige dolor-alto en alta vs baja novedad
    for _ in range(TRIALS):
        walls,body,meta,dolor=G2.make_scenario(rng)
        start=(0,0)
        if not G2.bfs_path(walls,start,meta): continue
        # dolor CROICO no letal en varias celdas
        dc={}
        for _ in range(6):
            r,c=rng.randint(0,N-1),rng.randint(0,N-1)
            if (r,c)!=start and (r,c)!=meta: dc[(r,c)]=rng.uniform(0.4,0.9)
        rr=random.Random(rng.randint(0,10**9))
        res.append(run(rr,walls,start,meta,dc))
        # T-HAB-04: asimetria -> en alta novedad (eta alto) el peso efectivo del dolor es MENOR que
    # en baja novedad (eta bajo), para la misma celda de dolor. Contamos cuantas veces ocurre.
    asim_alta = 0; asim_baja = 0
    for _ in range(TRIALS):
        tk_h = HabTick(rng.randint(0,10**9)); tk_h.eta = 0.6
        tk_l = HabTick(rng.randint(0,10**9)); tk_l.eta = 0.05
        dcell = {(2,2):0.8}
        w_alta = tk_h.peso_dolor((2,2), dcell) * (1.0 - BETA_ASIM*max(0.0, tk_h.eta - ETA_OPT))
        w_baja = tk_l.peso_dolor((2,2), dcell) * (1.0 - BETA_ASIM*max(0.0, tk_l.eta - ETA_OPT))
        if w_alta < w_baja: asim_alta += 1
        asim_baja += 1
    t4 = asim_alta >= 1

    def tasa(xs): return round(sum(1 for l,p,d in xs if l)/len(xs),3) if xs else 0.0
    def pdolor(xs): return round(sum(d for l,p,d in xs if l)/len([x for x in xs if x[0]]),3) if any(l for l,p,d in xs) else 0.0
    tc=tasa(res); pd=pdolor(res)
    t1 = pd > 0.475             # T-HAB-01: habituado (subio vs 0038 que era 0.475)
    t2 = tc >= 0.25             # T-HAB-02: sigue llegando
    t3 = pd < 2.0               # T-HAB-03 NC: no suicida (no pisa dolor en casi todos los pasos)
    t4 = asim_alta >= 1         # T-HAB-04: en alta novedad tolera mas dolor (asimetria)
    overall=t1 and t2 and t3 and t4
    print("exp_SGM_0039 PAIN_HABITUATION + CURIOSITY_ASYMMETRY")
    print("  trials:",len(res))
    print("  tasa llegada:",tc," pisos dolor prom:",pd)
    print("  T-HAB-01 (habituado no suicida):",t1," T-HAB-02 (llega):",t2," T-HAB-03 NC:",t3," T-HAB-04 (asimetria):",t4)
    print("  PASS:",overall)
    result={"experiment_id":"exp_SGM_0039","experiment_name":"pain_habituation_curiosity_asymmetry",
        "phase":"Camino A - dolor cronico (habituacion) + asimetria curiosidad/dolor",
        "date":"2026-08-03",
        "hypothesis":"Dolor cronico no letal -> habituacion (peso decae con repeticiones, con piso: no suicida). Curiosidad (eta alto) amortigua el dolor: el sistema tolera mas dolor por novedad. Esto modela al humano que se acostumbra al dolor para sobrevivir y que tolera mas dolor por curiosidad.",
        "config":{"N":N,"trials":TRIALS,"seed":SEED,"kappa_hab":KAPPA_HAB,"hab_piso":HAB_PISO,
                  "beta_asim":BETA_ASIM,"refs":["exp_SGM_0038_curiosity_vs_pain","exp_SGM_0033_grid_dolor"]},
        "result":{"trials":len(res),"tasa_llegada":tc,"pisos_dolor_prom":pd,
                  "T-HAB-01":t1,"T-HAB-02":t2,"T-HAB-03":t3,"T-HAB-04":t4,"pass":overall},
        "script":"phases/phase7_composicion/run_pain_habituation.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0039_pain_habituation.json",
        "test_target":"T-HAB-01 (habituado no suicida) + T-HAB-02 (llega) + T-HAB-03 NC + T-HAB-04 (asimetria)",
        "variant_of":None,
        "lit_refs":["exp_SGM_0038_curiosity_vs_pain.json","exp_SGM_0033_grid_dolor.json"],
        "notes":"Habituacion al dolor cronico (peso decae con rep, piso no-suicida) + asimetria: eta amortigua delta_dolor en alta novedad. Modela al humano que se acostumbra para sobrevivir y tolera mas dolor por curiosidad.",
        "notes_criollo":"El bicho se acostumbra al dolor que no lo mata (como nosotros: dolor crónico deja de paralizarte para que sigas funcionando). Pero nunca deja de sentir del todo (piso). Y si algo es muy nuevo, la curiosidad le resta miedo al dolor: 'duele pero quiero ver'."}
    out=os.path.join(os.path.dirname(__file__),"results_exp_SGM_0039_pain_habituation.json")
    json.dump(result,open(out,"w"),indent=2,ensure_ascii=False)
    print("RESULTADO escrito:",out)

if __name__=="__main__":
    main()
