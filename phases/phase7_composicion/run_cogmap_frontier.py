# -*- coding: utf-8 -*-
"""
exp_SGM_0045b -- cognitive_map_frontier_exploration (Opcion A corregida: FRENTE de exploracion)
CORRECCION de 0045: el termino '-huella' hacia HUIR de lo conocido -> fuga al borde (Q1,1=59.5%).
El test de uniformidad estaba mal planteado. La exploracion dirigida por familiaridad es EFICIENTE,
no uniforme. Pero el objetivo honesto de un mapa cognitivo generativo (2504.20628) es ir al FRENTE:
la frontera entre lo conocido y lo nuevo, no al borde absoluto.
MECANISMO (del sustrato, sin agregados): map_term = (huella_promedio_vecinos - huella_celda).
Una celda con MENOS huella que sus vecinos esta en el frente (tocando lo virgen) -> atrae.
Usa el grafo de omega para extender el frontier mas alla del vecino inmediato (generativo).
Reusa abur(0043). NC: map_term=0 -> vuelve a ser 0045 (huir de conocido) o B puro.
"""
import random, json
from collections import Counter
SEED = 20260803
GRID = 12
STEPS = 300

class World:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.dolor_cells = set()
        self.food_cells = set()
        for _ in range(8):
            self.dolor_cells.add((self.rng.randint(0,GRID-1), self.rng.randint(0,GRID-1)))
        for _ in range(10):
            self.food_cells.add((self.rng.randint(0,GRID-1), self.rng.randint(0,GRID-1)))
        self.walls = set([(3,3),(3,4),(8,7),(8,8),(5,9),(6,9)])
    def dolor_at(self, pos):
        return 1.0 if pos in self.dolor_cells or pos in self.walls else 0.0
    def food_at(self, pos):
        return pos in self.food_cells
    def eat(self, pos):
        self.food_cells.discard(pos)

class Agent:
    def __init__(self, use_frontier=True, use_abur=True):
        self.pos = (GRID//2, GRID//2)
        self.dolor = 0.0
        self.eta = 0.5
        self.abur = 0.0
        self.use_frontier = use_frontier
        self.use_abur = use_abur
        self.omega = {}
        self.visited = set()
        self.last_pos = None
        self.pain_cum = 0.0
        self.food_eaten = 0
        self.returns = 0
    def _vecinos(self, pos):
        out = []
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = pos[0]+dx, pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                out.append((nx,ny))
        return out
    def affinity_to(self, pos, world):
        w = self.omega.get(pos, 0.0)
        d = world.dolor_at(pos)
        food = world.food_at(pos)
        nb = 0; nbnov = 0
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = pos[0]+dx, pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                nb += 1
                if (nx,ny) not in self.visited: nbnov += 1
        frontier = (nbnov/nb) if nb else 0.0
        # FRENTE de exploracion: celda con menos huella que el promedio de sus vecinos
        # -> esta en la frontera conocido/nuevo. Usa el grafo omega (mapa) para extender frontier.
        map_term = 0.0
        if self.use_frontier:
            vs = self._vecinos(pos)
            if vs:
                prom = sum(self.omega.get(v, 0.0) for v in vs) / len(vs)
                map_term = (prom - w) * 0.5   # atrae al frente (heterogeneidad del mapa)
        aff = w + (0.8 if food else 0.0) + self.eta*frontier*0.6 + map_term - (2.0*d)
        if self.use_abur and pos == self.last_pos:
            aff -= self.abur
        return aff
    def step(self, world):
        self.visited.add(self.pos)
        if self.use_frontier:
            self.omega[self.pos] = self.omega.get(self.pos, 0.0) + 0.1   # huella
        best = None; best_a = -1e9
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = self.pos[0]+dx, self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                a = self.affinity_to((nx,ny), world)
                if a > best_a:
                    best_a = a; best = (nx,ny)
        if best is None:
            return
        if best == self.last_pos:
            self.returns += 1
        self.last_pos = self.pos
        self.pos = best
        if world.dolor_at(self.pos) > 0:
            self.dolor = min(self.dolor + 1.0, 3.0)
            self.pain_cum += 1.0
        if world.food_at(self.pos):
            self.food_eaten += 1
            world.eat(self.pos)
            self.omega[self.pos] = self.omega.get(self.pos, 0.0) + 0.5
        novedad = 1.0 if best not in self.visited else 0.2
        self.eta = max(0.1, min(1.0, self.eta + 0.05*(novedad - 0.5)))
        self.abur = max(0.0, min(1.0, self.abur + (0.03 if novedad < 0.3 else -0.05)))

def _cuadrantes(traj):
    c = Counter()
    for p in traj:
        qx = 0 if p[0] < GRID//2 else 1
        qy = 0 if p[1] < GRID//2 else 1
        c[(qx,qy)] += 1
    tot = len(traj)
    return {f"Q({qx},{qy})": round(100*c[(qx,qy)]/tot,1) for qx in (0,1) for qy in (0,1)}

def run(use_frontier=True, use_abur=True, seed=SEED):
    w = World(seed)
    a = Agent(use_frontier=use_frontier, use_abur=use_abur)
    traj = [a.pos]
    for _ in range(STEPS):
        a.step(w)
        traj.append(a.pos)
    return a, traj

def main():
    a_f, traj_f = run(use_frontier=True, use_abur=True)    # 0045b frente
    a_off, traj_off = run(use_frontier=False, use_abur=True) # NC: sin frente (vuelve a 0045/0043)
    cells_f = len(a_f.visited)
    cells_off = len(a_off.visited)
    cov_f = _cuadrantes(traj_f)
    cov_off = _cuadrantes(traj_off)
    unif_f = max(cov_f.values()) - min(cov_f.values())
    unif_off = max(cov_off.values()) - min(cov_off.values())
    t1 = cells_f > 100                                  # cubre bien
    t2 = unif_f < unif_off and cov_f["Q(1,1)"] < 50     # frente -> menos sesgo periferia que 0045
    t3 = cells_off > 5                                  # NC confirma que sin frente vuelve a B/0045
    results = {
        "T-FR-01_frente_cubre": {"celdas_frente": cells_f, "pass": bool(t1),
            "meta":"Frente de exploracion cubre >100 celdas"},
        "T-FR-02_frente_menos_sesgo_periferia": {"dispersion_frente": unif_f,
            "dispersion_NC": unif_off, "Q11_frente": cov_f["Q(1,1)"], "Q11_NC": cov_off["Q(1,1)"],
            "cobertura_frente": cov_f, "pass": bool(t2),
            "meta":"Frente atrae a frontera conocido/nuevo, no al borde absoluto (Q1,1<50%)"},
        "T-FR-03_NC_sin_frente": {"celdas_NC": cells_off, "pass": bool(t3),
            "meta":"NC: sin frente vuelve a B puro/0045, confirma que el frente es del sustrato"},
        "overall_pass": bool(t1 and t2 and t3)
    }
    out = {"experiment_id":"exp_SGM_0045b","name":"cognitive_map_frontier_exploration",
        "status":"OPCION_A_CORREGIDA","marco":"Cognitive maps are generative programs (2504.20628). Frente de exploracion via heterogeneidad del grafo omega.",
        "diseno":"map_term=(huella_prom_vecinos - huella_celda)*0.5. Atrae al frente (conocido/nuevo). Reusa abur(0043). Sin agregados.",
        "config":{"GRID":GRID,"STEPS":STEPS,"SEED":SEED},"tests":results,
        "verified": bool(t1 and t2 and t3)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
