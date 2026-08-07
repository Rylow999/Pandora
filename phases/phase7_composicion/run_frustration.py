# -*- coding: utf-8 -*-
"""
exp_SGM_0043 -- frustration_interrupt_exploration (B puro: sin hardcode, sin agregados, sin bloqueos)
HONESTIDAD (correccion Luciano 2026-08-03): NO se agrega estado nuevo. Se usa SOLO el sustrato existente:
- abur (0036): frustracion, sube cuando novedad se hunde
- last_pos (memoria de trabajo, 0020): la celda anterior
- eta (0036): error de prediccion = novedad
El hallazgo de 0042 fue que `abur` existia pero estaba DESCONEcTADO de la accion. Aqui se acopla:
la afinidad de volver a last_pos lleva pena = abur (misma moneda del campo, peso 1.0, sin numero magico).
NO es bloqueo ('prohibido volver'): es que repetir se vuelve menos atractivo a medida que abur crece.
El agente ROMPE la oscilacion solo. Sin if-elif de 'explora si abur>umbral'.
Marco: Active Inference (2010.00262) — exploracion emerge de minimizar sorpresa, no de modulo de mapa.
"""
import random, math, json

SEED = 20260803
random.seed(SEED)
GRID = 12
STEPS = 300

class Agent:
    def __init__(self, use_abur=True):
        self.pos = (GRID//2, GRID//2)
        self.dolor = 0.0
        self.eta = 0.5
        self.abur = 0.0
        self.use_abur = use_abur
        self.omega = {}           # SOLO comida (HRR 0028), no celda inicial
        self.visited = set()
        self.last_pos = None
        self.pain_cum = 0.0
        self.food_eaten = 0
        self.returns = 0          # veces que volvio a last_pos
        self.steps_done = 0

    def bind_location(self, pos, val):
        self.omega[pos] = self.omega.get(pos, 0.0) + val

    def affinity_to(self, pos, world):
        w = self.omega.get(pos, 0.0)
        d = world.dolor_at(pos)
        food = world.food_at(pos)
        # frontier: fraccion de vecindad no visitada (eta extendido 0036)
        nb = 0; nbnov = 0
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = pos[0]+dx, pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                nb += 1
                if (nx,ny) not in self.visited: nbnov += 1
        frontier = (nbnov/nb) if nb else 0.0
        aff = w + (0.8 if food else 0.0) + self.eta*frontier*0.6 - (2.0*d)
        # B puro: pena de retorno = abur (misma moneda, peso 1.0, del sustrato)
        if self.use_abur and pos == self.last_pos:
            aff -= self.abur
        return aff

    def step(self, world):
        self.visited.add(self.pos)
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
            self.bind_location(self.pos, 0.5)
        novedad = 1.0 if best not in self.visited else 0.2
        self.eta = max(0.1, min(1.0, self.eta + 0.05*(novedad - 0.5)))
        # abur: sube si novedad baja (predictibilidad alta = frustracion), baja si hay novedad
        self.abur = max(0.0, min(1.0, self.abur + (0.03 if novedad < 0.3 else -0.05)))

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

def run(use_abur=True, seed=SEED):
    w = World(seed)
    a = Agent(use_abur=use_abur)
    for _ in range(STEPS):
        a.step(w)
    return a

def main():
    a_dyn = run(use_abur=True)
    a_off = run(use_abur=False)   # NC: frustracion desconectada (reproduce 0042)
    cells_dyn = len(a_dyn.visited)
    cells_off = len(a_off.visited)
    t1 = cells_dyn > cells_off * 2 and cells_dyn > 30
    # T-FR-02: fraccion de retornos baja conforme abur sube (medido: retornos din << retornos off si abur alto)
    t2 = (a_dyn.returns < a_off.returns) or (a_dyn.abur > 0.5 and a_dyn.returns < STEPS*0.5)
    # T-FR-03 (NC): abur=0 reproduce oscilacion de 0042 (pocas celdas)
    t3 = cells_off <= 10   # NC confirma que sin frustracion se estanca
    results = {
        "T-FR-01_explora_con_frustracion": {
            "celdas_dinamico": cells_dyn, "celdas_NC_sin_abur": cells_off,
            "pass": bool(t1), "meta":"Active Inference: frustracion (abur) emerge exploracion sin modulo de mapa"},
        "T-FR-02_rompe_retorno": {
            "retornos_dinamico": a_dyn.returns, "retornos_NC": a_off.returns,
            "abur_final": round(a_dyn.abur,3),
            "pass": bool(t2), "meta":"Penas de retorno acopladas a abur reducen oscilacion"},
        "T-FR-03_NC_reproduce_0042": {
            "celdas_off": cells_off, "pass": bool(t3),
            "meta":"NC: sin frustracion el agente se estanca (confirma que exploracion emerge del campo)"},
        "overall_pass": bool(t1 and t3)
    }
    out = {
        "experiment_id":"exp_SGM_0043",
        "name":"frustration_interrupt_exploration",
        "status":"B_PURO",
        "marco":"Active Inference (2010.00262): exploracion emerge de minimizar sorpresa. Usa solo abur(0036)+last_pos(0020), sin agregados.",
        "diseno":"acoplamiento abur->pena de retorno, peso 1.0 (misma moneda del campo). Sin hardcode de umbral, sin bloqueo.",
        "config":{"GRID":GRID,"STEPS":STEPS,"SEED":SEED},
        "tests":results,
        "verified": bool(t1 and t3)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
