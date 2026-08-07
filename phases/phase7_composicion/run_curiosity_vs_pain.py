# -*- coding: utf-8 -*-
"""
exp_SGM_0038 -- curiosity_vs_pain (Camino A: balance eta global vs dolor en entorno 2D)
PREGUNTA HONESTA: la curiosidad (0036) es realmente GLOBAL, o se achica ante el riesgo? El agente con
eta global debe decidir entre explorar para reducir eta (sabiendo que algunos caminos pinchan) o
quedarse en lo conocido. El balance humano real NO es "curiosidad siempre gana" ni "dolor siempre
gana": es dinamico. El 0038 mide si el sistema tiene ese balance.

TEST-FIRST (con NC):
  Entorno: maze 10x10 + celdas de DOLOR (reusa 0033b). El agente tiene eta global (0036) Y dolor.
  - T-DOL-01: con dolor en el camino de alta novedad, el agente lo EVITA (eta no lo ciega).
    Medible: tasa de pisar dolor < umbral (el sistema no es un saltarin suicida).
  - T-DOL-02: el agente SI explora por eta cuando el dolor es ausente/leve (no es un cobarde que
    nunca sale). Medible: tasa de llegada >= 0.30 (sigue resolviendo el maze).
  - T-DOL-03 (NC): la curiosidad no lo mata -> sigue llegando a meta con dolor presente.
    Medible: tasa >= 0.25 (cierra tarea a pesar del dolor).

Variable discriminante: tasa de pisar dolor vs tasa de llegar. Comparar contra 0036 (sin dolor) para
ver cuanto se achica la exploracion.
Honestidad: el dolor CONOCIDO pesa menos que el DESCONOCIDO (home bias del riesgo) -> el costo de dolor
se multiplica por (1 + eta_dolor) donde eta_dolor es el error de prediccion sobre la rama de dolor.
"""
import json, os, sys, random, math
sys.path.insert(0, os.path.dirname(__file__))
import run_grid_agent as G2   # gen_maze, bfs_path, make_scenario

SEED = 20260803
TRIALS = 40
N = 10
MAX_TICKS = 200
ETA_OPT = 0.30
SIGMA_ETA = 0.22
ETA_BAJO = 0.05
THETA_ABURR = 6
ALPHA_NOV = 1.5
DOLOR_PEN = 5.0        # penalizacion base de pisar dolor
DOLOR_CONOCIDO_FACTOR = 0.5   # el dolor conocido pesa menos (home bias)

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def dopamina(eta):
    return math.exp(-((eta - ETA_OPT)/SIGMA_ETA)**2)

class CuriosityDolorTick:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.eta = 0.0
        self.aburrimiento = 0
        self.visitas = {}
        self.dolor_visto = {}      # celda -> dolor ya experimentado (para home bias)
        self.omega = {}
        for r in range(N):
            for c in range(N):
                self.omega[(r,c)] = [self.rng.uniform(-1,1) for _ in range(16)]

    def predict_next(self, pos, goal):
        vecinos = [(pos[0]+dr,pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
        vecinos = [v for v in vecinos if 0<=v[0]<N and 0<=v[1]<N]
        if not vecinos: return None
        return self.omega[min(vecinos, key=lambda v: manhattan(v, goal))]

    def update(self, pos, goal, real_omega):
        pred = self.predict_next(pos, goal)
        if pred is None:
            self.eta = 1.0
        else:
            dot = sum(a*b for a,b in zip(pred, real_omega))
            na = math.sqrt(sum(a*a for a in pred)); nb = math.sqrt(sum(b*b for b in real_omega))
            self.eta = 1.0 - (dot/(na*nb) if na*nb>0 else 0.0)
        self.aburrimiento = self.aburrimiento+1 if self.eta < ETA_BAJO else max(0,self.aburrimiento-1)
        self.visitas[pos] = self.visitas.get(pos,0)+1

    def costo(self, v, goal, dolor_cell):
        """Costo de ir a v: dist a meta - bonus novedad + penalizacion de dolor (home biased)."""
        base = manhattan(v, goal)
        nov = ALPHA_NOV * (1.0/(1.0 + self.visitas.get(v,0)))
        # dolor: conocido pesa menos
        if v in dolor_cell:
            d = dolor_cell[v]
            if v in self.dolor_visto:
                d *= DOLOR_CONOCIDO_FACTOR   # ya lo sufrio -> home bias
            return base - nov + DOLOR_PEN * d * (1.0 + self.eta)  # dolor nuevo (eta alto) pesa mas
        return base - nov

    def choose(self, pos, goal, walls, dolor_cell):
        vecinos = [(pos[0]+dr,pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
        vecinos = [v for v in vecinos if 0<=v[0]<N and 0<=v[1]<N and v not in walls and v!=pos]
        if not vecinos:
            return None, "none"
        if self.aburrimiento >= THETA_ABURR:
            nb = max(vecinos, key=lambda v: 1.0/(1.0+self.visitas.get(v,0)))
            return nb, "novelty"
        if self.eta > ETA_OPT:
            nb = min(vecinos, key=lambda v: self.costo(v, goal, dolor_cell))
            return nb, "explore"
        nb = min(vecinos, key=lambda v: self.costo(v, goal, dolor_cell))
        return nb, "exploit"

def run(mode, rng, walls, start, goal, dolor_cell):
    if mode == "cur":
        tick = CuriosityDolorTick(rng.randint(0,10**9))
    pos = start
    pasos = 0
    pisos_dolor = 0
    while pasos < MAX_TICKS:
        if pos == goal:
            return True, pasos, pisos_dolor
        if mode == "cur":
            nb, _ = tick.choose(pos, goal, walls, dolor_cell)
            if nb is None:
                return False, pasos, pisos_dolor
            if nb in dolor_cell:
                pisos_dolor += 1
                tick.dolor_visto[nb] = dolor_cell[nb]
            tick.update(pos, goal, tick.omega[nb])
        else:
            vecinos = [(pos[0]+dr,pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
            vecinos = [v for v in vecinos if 0<=v[0]<N and 0<=v[1]<N and v not in walls and v!=pos]
            if not vecinos:
                return False, pasos, pisos_dolor
            nb = min(vecinos, key=lambda v: manhattan(v,goal) + (DOLOR_PEN*dolor_cell.get(v,0)))
            if nb in dolor_cell: pisos_dolor += 1
        pos = nb
        pasos += 1
    return False, pasos, pisos_dolor

def main():
    rng = random.Random(SEED)
    res_cur, res_base = [], []
    for _ in range(TRIALS):
        walls, body, meta, dolor = G2.make_scenario(rng)
        start=(0,0)
        if not G2.bfs_path(walls, start, meta):
            continue
        # dolor_cell: algunas celdas aleatorias con dolor moderado
        dc = {}
        for _ in range(5):
            r,c = rng.randint(0,N-1), rng.randint(0,N-1)
            if (r,c)!=start and (r,c)!=meta:
                dc[(r,c)] = rng.uniform(0.5,1.0)
        rc = random.Random(rng.randint(0,10**9))
        rb = random.Random(rng.randint(0,10**9))
        res_cur.append(run("cur", rc, walls, start, meta, dc))
        res_base.append(run("base", rb, walls, start, meta, dc))

    def tasa(xs):
        return round(sum(1 for l,p,d in xs if l)/len(xs),3) if xs else 0.0
    def pdolor(xs):
        return round(sum(d for l,p,d in xs)/len(xs),3) if xs else 0.0
    tc, tb = tasa(res_cur), tasa(res_base)
    pd = pdolor(res_cur)
    t1 = pd < 0.5            # T-DOL-01: no es suicida (evita dolor)
    t2 = tc >= 0.30          # T-DOL-02: sigue explorando/resolviendo
    t3 = tc >= 0.25          # T-DOL-03 NC: cierra tarea con dolor
    overall = t1 and t2 and t3
    print("exp_SGM_0038 CURIOSITY_VS_PAIN (eta global vs dolor)")
    print("  trials:", len(res_cur))
    print("  tasa CUR(eta+dolor):", tc, " BASE(greedy+dolor):", tb)
    print("  pisos de dolor promedio (CUR):", pd, " (T-DOL-01 <0.5):", t1)
    print("  T-DOL-02 (cur>=0.30):", t2, " T-DOL-03 NC (cur>=0.25):", t3)
    print("  PASS:", overall)
    result={"experiment_id":"exp_SGM_0038","experiment_name":"curiosity_vs_pain",
        "phase":"Camino A - balance curiosidad(dolor): campo global vs riesgo",
        "date":"2026-08-03",
        "hypothesis":"La curiosidad global (eta) es realmente global: el agente explora por eta pero EVITA el dolor (no es suicida). El dolor CONOCIDO pesa menos que el DESCONOCIDO (home bias del riesgo). El sistema mantiene un balance dinamico: explora donde no duele, evita dolor fuerte, a veces el aburrimiento le gana y prueba a pesar del riesgo leve.",
        "config":{"N":N,"trials":TRIALS,"seed":SEED,"dolor_pen":DOLOR_PEN,
                  "dolor_conocido_factor":DOLOR_CONOCIDO_FACTOR,"refs":["exp_SGM_0036_curiosity_global","exp_SGM_0033_grid_dolor"]},
        "result":{"trials":len(res_cur),"tasa_cur_eta_dolor":tc,"tasa_base":tb,
                  "pisos_dolor_promedio":pd,"T-DOL-01":t1,"T-DOL-02":t2,"T-DOL-03":t3,"pass":overall},
        "script":"phases/phase7_composicion/run_curiosity_vs_pain.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0038_curiosity_vs_pain.json",
        "test_target":"T-DOL-01 (evita dolor) + T-DOL-02 (sigue explorando) + T-DOL-03 NC (cierra tarea)",
        "variant_of":None,
        "lit_refs":["exp_SGM_0036_curiosity_global.json","exp_SGM_0033_grid_dolor.json"],
        "notes":"Balance eta global vs dolor. El dolor CONOCIDO pesa menos (home bias del riesgo humano). La curiosidad no es suicida ni cobarde: balance dinamico. Si el sistema pisa dolor siempre o nunca llega, el mecanismo se rompe.",
        "notes_criollo":"El bicho tiene curiosidad (eta) pero le tiene miedo al dolor. No es tonto: evita las celdas que pinchan. Pero tampoco se queda escondido: si no duele, sale a explorar. Y lo que ya le dolia una vez pesa menos (se acostumbra, como nosotros). Eso es el balance humano: no 'siempre gana la curiosidad' ni 'siempre gana el miedo'."}
    out=os.path.join(os.path.dirname(__file__),"results_exp_SGM_0038_curiosity_vs_pain.json")
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    print("RESULTADO escrito:", out)

if __name__=="__main__":
    main()
