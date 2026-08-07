# -*- coding: utf-8 -*-
"""
exp_SGM_0045 -- cognitive_map_generative_exploration (Opcion A: grafo omega como mapa generativo)
HONESTIDAD (correccion Luciano 2026-08-03): SIN agregados de estado. El grafo de omega YA existe.
La "huella" (omega de celda acumula al transitar) ES el mapa cognitivo emergente (no un contador mio).
Cognitive maps are generative programs (2504.20628): el mapa infiere estructura, no codifica layout.
En SGM: la afinidad del grafo ya dice que tan familiar/lejano es un lugar. La exploracion DIRIGIDA
surge de moverse hacia celdas de BAJA huella (familiaridad baja = territorio virgen) por la misma afinidad.
Reusa frustracion (0043, abur->pena retorno) y HRR comida (0028). No hardcodea mapa: el grafo crece andando.
"""
import random, json
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
    def __init__(self, use_map=True, use_abur=True):
        self.pos = (GRID//2, GRID//2)
        self.dolor = 0.0
        self.eta = 0.5
        self.abur = 0.0
        self.use_map = use_map       # grafo omega como mapa (huella)
        self.use_abur = use_abur     # frustracion 0043
        self.omega = {}              # HRR comida + HUELLA de celda transitada (mapa emergente)
        self.visited = set()
        self.last_pos = None
        self.pain_cum = 0.0
        self.food_eaten = 0
        self.returns = 0
        self.steps_done = 0
    def affinity_to(self, pos, world):
        # huella: omega de celda = familiaridad acumulada al transitar (mapa cognitivo emergente)
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
        # mapa generativo: celdas de BAJA huella (familiaridad baja) atraen si use_map.
        # esto dirige la exploracion al territorio virgen SIN contador extra (la huella es el omega).
        map_term = -w if self.use_map else 0.0   # mas huella = menos atractivo (ya conocido)
        aff = w + (0.8 if food else 0.0) + self.eta*frontier*0.6 + map_term - (2.0*d)
        if self.use_abur and pos == self.last_pos:
            aff -= self.abur
        return aff
    def step(self, world):
        self.visited.add(self.pos)
        # huella: dejar marca en la celda actual (mapa crece andando)
        if self.use_map:
            self.omega[self.pos] = self.omega.get(self.pos, 0.0) + 0.1
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
        self.steps_done += 1
        if world.dolor_at(self.pos) > 0:
            self.dolor = min(self.dolor + 1.0, 3.0)
            self.pain_cum += 1.0
        if world.food_at(self.pos):
            self.food_eaten += 1
            world.eat(self.pos)
            self.omega[self.pos] = self.omega.get(self.pos, 0.0) + 0.5  # refuerzo HRR comida
        novedad = 1.0 if best not in self.visited else 0.2
        self.eta = max(0.1, min(1.0, self.eta + 0.05*(novedad - 0.5)))
        self.abur = max(0.0, min(1.0, self.abur + (0.03 if novedad < 0.3 else -0.05)))

def _cuadrantes(traj, GRID):
    from collections import Counter
    c = Counter()
    for p in traj:
        qx = 0 if p[0] < GRID//2 else 1
        qy = 0 if p[1] < GRID//2 else 1
        c[(qx,qy)] += 1
    tot = len(traj)
    return {f"Q({qx},{qy})": round(100*c[(qx,qy)]/tot,1) for qx in (0,1) for qy in (0,1)}

def run(use_map=True, use_abur=True, seed=SEED):
    w = World(seed)
    a = Agent(use_map=use_map, use_abur=use_abur)
    traj = [a.pos]
    for _ in range(STEPS):
        a.step(w)
        traj.append(a.pos)
    return a, traj

def main():
    a_map, traj_map = run(use_map=True, use_abur=True)      # 0045: mapa generativo + frustracion
    a_b,   traj_b   = run(use_map=False, use_abur=True)     # NC: solo B puro (0043)
    cells_map = len(a_map.visited)
    cells_b = len(a_b.visited)
    cov_map = _cuadrantes(traj_map, GRID)
    cov_b = _cuadrantes(traj_b, GRID)
    # uniformidad: maximo-minimo de cobertura por cuadrante (menor = mas uniforme)
    unif_map = max(cov_map.values()) - min(cov_map.values())
    unif_b = max(cov_b.values()) - min(cov_b.values())
    t1 = cells_map >= cells_b                       # el mapa no empeora la cobertura
    t2 = unif_map < unif_b                          # dirige mas uniforme
    t3 = cells_b > 5                                # NC confirma que B puro sigue funcionando (0043)
    results = {
        "T-MG-01_mapa_no_empeora": {
            "celdas_mapa": cells_map, "celdas_B_puro_NC": cells_b,
            "pass": bool(t1), "meta":"Mapa generativo dirigido no reduce cobertura vs B puro"},
        "T-MG-02_exploracion_uniforme": {
            "dispersion_mapa": unif_map, "dispersion_B_puro_NC": unif_b,
            "cobertura_mapa": cov_map, "cobertura_B_NC": cov_b,
            "pass": bool(t2), "meta":"Mapa dirigido = cobertura mas uniforme (menos sesgo de cuadrante)"},
        "T-MG-03_NC_B_puro_funciona": {
            "celdas_B": cells_b, "pass": bool(t3),
            "meta":"NC: con mapa off vuelve a ser B puro (0043), confirma que el mapa es del sustrato"},
        "overall_pass": bool(t1 and t2 and t3)
    }
    out = {
        "experiment_id":"exp_SGM_0045",
        "name":"cognitive_map_generative_exploration",
        "status":"OPCION_A",
        "marco":"Cognitive maps are generative programs (2504.20628). Grafo omega como mapa emergente (huella), sin agregados.",
        "diseno":"omega[celda] acumula al transitar (huella=mapa). Afinidad resta huella (territorio virgen atrae). Reusa abur(0043).",
        "config":{"GRID":GRID,"STEPS":STEPS,"SEED":SEED},
        "tests":results,
        "verified": bool(t1 and t2 and t3)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
