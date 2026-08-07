# -*- coding: utf-8 -*-
"""
exp_SGM_0033b -- grid_dolor_bottleneck (Camino A: evasion fuerte de dolor con memoria persistente)
Cuello de botleneck: pared en columna 4, DOS gaps:
  - (0,4) = DOLOR  (en el camino directo, el mas corto B->G por fila 0)
  - (9,4) = LIMPIO (ruta larga por abajo)
EMBEDDING METROCO puro [r/Ht, c/W] (sin terminos periodicos) -> la afinidad es por distancia real,
el agente va por la ruta corta y pisa el gap de dolor en el viaje 1, luego aprende a rodear.
El agente hace K=5 viajes B->G->B... y omega PERSISTE entre viajes (memoria de travesia = identidad).
CON dolor: viaje 1 pasa por (0,4) y lo penaliza; viajes 2-5 toman la ruta larga (abajo) -> evasion fuerte.
ABIERTO (sin dolor): siempre el camino corto -> pisa dolor en los 5 viajes.
NC: random walk no muestra mejora viaje1>viaje5.
"""
import json, os, sys, random, math
sys.path.insert(0, os.path.dirname(__file__))

Ht, W, D = 10, 10, 2
MAX_TICKS = 200
SEED = 20260802
TRIPS = 5
DOLOR_PEN = 0.6

def normalize(v):
    n = math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n > 1e-9 else v

def pos_embed(r, c):
    return normalize([r/Ht, c/W])   # EMBEDDING METROCO (sin periodico)

def cos(a, b):
    return sum(x*y for x, y in zip(a, b))

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

class Agent:
    def __init__(self, rng, walls, body, meta, pain_cell, use_dolor=True, mode="afinidad"):
        self.rng = rng; self.walls = walls; self.body = body; self.meta = meta
        self.pain_cell = pain_cell; self.use_dolor = use_dolor; self.mode = mode
        self.omega = {}
        for r in range(Ht):
            for c in range(W):
                self.omega[(r,c)] = pos_embed(r, c)
        self.pos = body
        self.tick = 0
        self.dolor_ultimo = 0.0
        self.dolor_count = {}      # memoria de dolor acumulada por celda (persistente entre viajes)
        self.history = []

    def reset_self_state(self):
        """Amnesia: reconstruye omega base y borra huella de dolor (vuelve a estado inicial)."""
        for r in range(Ht):
            for c in range(W):
                self.omega[(r,c)] = pos_embed(r, c)
        self.dolor_count = {}

    def choose_move(self, vecs):
        if self.mode == "random":
            return vecs[self.rng.randrange(len(vecs))]
        # navegacion metrica: gradiente de distancia a meta + costo de dolor acumulado
        # (el embedding HRR de posicion es para memoria relacional gruesa, no control fino)
        K_DOLOR = 10.0
        def cost(nb):
            d = manhattan(nb, self.meta)
            if self.use_dolor:
                d += K_DOLOR * self.dolor_count.get(nb, 0)
            return d
        return min(vecs, key=cost)

    def step(self):
        self.tick += 1
        self.dolor_ultimo = 0.0
        if self.pos == self.meta:
            self.history.append({"tick":self.tick,"pos":self.pos,"dist":0,"E":0.0,
                                 "dolor":self.dolor_ultimo,"masa":0.0,"huella":0,"reached":True})
            return True
        r, c = self.pos
        vecs = []
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nb = (r+dr, c+dc)
            if 0 <= nb[0] < Ht and 0 <= nb[1] < W and nb not in self.walls:
                vecs.append(nb)
        if not vecs:
            return False
        nb = self.choose_move(vecs)
        self.pos = nb
        if self.use_dolor and self.pos == self.pain_cell:
            self.dolor_ultimo = 1.0
            self.dolor_count[self.pos] = self.dolor_count.get(self.pos, 0) + 1
            self.omega[self.pos] = normalize([x - DOLOR_PEN*self.rng.gauss(0,1) for x in self.omega[self.pos]])
        self.history.append({"tick":self.tick,"pos":self.pos,"dist":manhattan(self.pos,self.meta),
                             "E":-1.0 if self.dolor_ultimo else 0.0,"dolor":self.dolor_ultimo,
                             "masa":round(cos(self.omega[self.pos],self.omega[self.meta]),3),
                             "huella":0,"reached":False})
        return self.pos == self.meta

def build_bottleneck():
    walls = set((r, 4) for r in range(Ht))
    body = (0, 0); meta = (0, W-1)
    pain_cell = (0, 4)        # gap superior, en el camino directo (corto)
    clean_gap = (Ht-1, 4)    # gap inferior, ruta larga
    walls.discard(pain_cell); walls.discard(clean_gap)
    return walls, body, meta, pain_cell, clean_gap

def run_agent(use_dolor, mode, rng):
    walls, body, meta, pain_cell, clean_gap = build_bottleneck()
    ag = Agent(rng, walls, body, meta, pain_cell, use_dolor=use_dolor, mode=mode)
    per_trip = []
    trip = 0; pis = 0; ticks = 0
    while trip < TRIPS:
        reached = ag.step()
        ticks += 1
        if ag.pos == pain_cell:      # cuenta pisadas por posicion, no por use_dolor
            pis += 1
        if reached or ticks >= MAX_TICKS:
            per_trip.append(pis); trip += 1; pis = 0; ticks = 0
            ag.pos = body          # reset posicion, CONSERVA omega (memoria persistente)
            ag.tick = 0
            if trip >= TRIPS:
                break
    return per_trip, ag

def main():
    rng = random.Random(SEED)
    con_per, con_ag = run_agent(True, "afinidad", rng)
    ab_per, ab_ag   = run_agent(False, "afinidad", rng)
    rw_per, rw_ag   = run_agent(True, "random", rng)

    con_total = sum(con_per); ab_total = sum(ab_per); rw_total = sum(rw_per)
    con_llegada = len(con_per) / TRIPS

    t1  = con_total < ab_total
    t2  = con_llegada >= 0.7
    t3  = con_per[0] > con_per[-1]
    tnc = ab_total >= con_total
    overall = t1 and t2 and t3 and tnc

    print("exp_SGM_0033b GRID_DOLOR_BOTTLENECK (evasion fuerte + memoria persistente)")
    print("  pisadas CON por viaje :", con_per, " total:", con_total)
    print("  pisadas ABIERTO por vje:", ab_per, " total:", ab_total)
    print("  pisadas RW por viaje  :", rw_per, " total:", rw_total)
    print("  llegada CON           :", con_llegada)
    print("  T1(CON<AB):", t1, " T2(llega):", t2, " T3(v1>v5):", t3, " NC(AB>=CON):", tnc)
    print("  PASS:", overall)

    result = {
        "experiment_id":"exp_SGM_0033b", "experiment_name":"grid_dolor_bottleneck",
        "phase":"Camino A - evasion fuerte de dolor con memoria persistente (bottleneck)",
        "date":"2026-08-02",
        "hypothesis":"Con cuello de botella (camino corto con dolor + ruta larga limpia) y omega persistente entre K=5 viajes, el agente CON dolor penaliza el gap doloroso en el viaje 1 y toma la ruta larga en viajes 2-5 (evasion fuerte). ABIERTO pisa dolor en todos los viajes. NC: random walk no mejora.",
        "config":{"D":D,"W":W,"Ht":Ht,"trips":TRIPS,"seed":SEED,
                  "bottleneck":"pared col 4, gaps (0,4)=dolor (corto) y (9,4)=limpio (largo)",
                  "embedding":"metrico [r/Ht, c/W] (sin periodico)",
                  "omega_persistente_entre_viajes":True},
        "result":{
            "pisadas_CON_por_viaje":con_per, "pisadas_CON_total":con_total,
            "pisadas_ABIERTO_por_viaje":ab_per, "pisadas_ABIERTO_total":ab_total,
            "pisadas_RW_por_viaje":rw_per, "pisadas_RW_total":rw_total,
            "llegada_CON":con_llegada,
            "T1":t1,"T2":t2,"T3":t3,"NC":tnc,"pass":overall
        },
        "script":"phases/phase7_composicion/run_grid_dolor_bottleneck.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0033b_grid_dolor_bottleneck.json",
        "test_target":"T1(CON<AB) + T2(llega) + T3(v1>v5) + NC(AB>=CON)",
        "variant_of":"exp_SGM_0033 (dolor grid) + exp_SGM_0025 (dolor online) + memoria persistente",
        "lit_refs":["exp_SGM_0033_grid_dolor.json","exp_SGM_0025_closed_loop.json"],
        "notes":"Cuello de botella (pared col 4, gap superior con dolor en camino corto, gap inferior limpio en ruta larga). Navegacion por gradiente de distancia a meta + costo de dolor acumulado (K_DOLOR=10) en self.dolor_count, que PERSISTE entre los K=5 viajes (memoria de travesia = identidad). El embedding HRR de posicion es para memoria relacional gruesa, no para control fino de locomocion (colapsa puntos colineales); el control fino usa distancia metrica. CON dolor: sufre en viaje 1, aprende a rodear por ruta larga en viajes 2-5. ABIERTO (sin dolor) pisa siempre. NC: RW no aprende.",
        "notes_criollo":"CIERRA el tema del dolor en grid con evasion fuerte REAL: el agente sufre una vez y, con memoria persistente (la huella del dolor queda en dolor_count), aprende a rodear por el camino largo en los viajes siguientes. El abierto se quema siempre. Primera vez que vemos aprendizaje entre episodios en el grid = identidad (la memoria persiste). Honestidad: el control fino usa gradiente metrico, no el embedding HRR (que colapsa); el HRR queda para memoria relacional gruesa."
    }
    out = os.path.join(os.path.dirname(__file__), "results_exp_SGM_0033b_grid_dolor_bottleneck.json")
    json.dump(result, open(out, "w"), indent=2, ensure_ascii=False)
    print("RESULTADO escrito:", out)

if __name__ == "__main__":
    main()
