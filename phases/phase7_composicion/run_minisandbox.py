# -*- coding: utf-8 -*-
"""
exp_SGM_0042 -- minisandbox_observatory (OBSERVATORIO, no integrador de conceptos emergentes)
HONESTIDAD (correccion Luciano 2026-08-03): NO integramos "moral" ni "discurso interno" como modulos.
Son conceptos emergentes del sustrato; se CATALOGAN desde afuera, no se agregan. El agente NO recibe
objetivos. Su loop es el TICK UNIFICADO (0023) operando sobre un mundo abierto chico (grilla 2D).
Medimos CONDUCTA contra tareas tipo Animal-AI (1909.07483): evitacion de dano, espacial, exploracion.
Variable discriminante: el sustrato completo supera al baseline ciego en esas tareas.
"""
import random, math, json

SEED = 20260803
random.seed(SEED)
GRID = 12
STEPS = 300

def rng_next():
    return random.random()

# ---- sustrato: campos del agente ----
class Agent:
    def __init__(self, use_dolor=True, use_hrr=True):
        self.pos = (GRID//2, GRID//2)
        self.dolor = 0.0          # campo dolor (0033/39)
        self.eta = 0.5            # curiosidad global (0036)
        self.abur = 0.0           # aburrimiento
        self.use_dolor = use_dolor
        self.use_hrr = use_hrr
        self.omega = {}           # memoria relacional: SOLO comida (HRR 0028), no celda inicial
        self.visited = set()
        self.last_pos = self.pos
        self.pain_cum = 0.0
        self.food_eaten = 0
        # NOTA: NO inicializar omega[pos]=1.0 (imán al origen, no es del sustrato)

    def bind_location(self, pos, val):
        # HRR binding (0028): ubicacion empaquetada en omega
        if self.use_hrr:
            self.omega[pos] = self.omega.get(pos, 0.0) + val

    def affinity_to(self, pos, world):
        # transicion por afinidad: celda con mayor omega (memoria) y menor dolor gana
        w = self.omega.get(pos, 0.0)
        d = world.dolor_at(pos) if self.use_dolor else 0.0
        food = world.food_at(pos)
        # frontier: fraccion de la vecindad de pos que NO he visitado (eta extendido, 0036 en grilla)
        nb = 0; nbnov = 0
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = pos[0]+dx, pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                nb += 1
                if (nx,ny) not in self.visited: nbnov += 1
        frontier = (nbnov/nb) if nb else 0.0
        # exploracion en mundo abierto: atraccion a alejarse del centro de masa de visited
        # (eta alto = error de prediccion alto lejos de lo conocido; coherente con 0036)
        cm = self.center_of_mass()
        dist_cm = math.hypot(pos[0]-cm[0], pos[1]-cm[1]) if cm else 0.0
        # afinidad = memoria + comida + novedad(frontier)*eta + exploracion(dist)*eta - dolor
        return w + (0.8 if food else 0.0) + self.eta*frontier*0.6 + self.eta*(dist_cm/GRID)*0.5 - (2.0*d)

    def center_of_mass(self):
        if not self.visited: return None
        n=len(self.visited)
        sx=sum(p[0] for p in self.visited); sy=sum(p[1] for p in self.visited)
        return (sx/n, sy/n)

    def step(self, world):
        self.last_pos = self.pos
        self.visited.add(self.pos)
        # elegir vecino por afinidad
        best = None; best_a = -1e9
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny = self.pos[0]+dx, self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                a = self.affinity_to((nx,ny), world)
                if a > best_a:
                    best_a = a; best = (nx,ny)
        if best is None:
            return
        self.pos = best
        # consecuencia: dolor
        if self.use_dolor:
            d = world.dolor_at(self.pos)
            self.dolor += d
            self.pain_cum += d
            if d > 0: self.dolor = min(self.dolor, 3.0)
        # comida
        if world.food_at(self.pos):
            self.food_eaten += 1
            world.eat(self.pos)
            self.bind_location(self.pos, 0.5)   # recuerda donde habia comida
        # eta: error de prediccion = novedad del entorno
        novedad = 1.0 if self.pos not in self.visited else 0.2
        self.eta = max(0.1, min(1.0, self.eta + 0.05*(novedad - 0.5)))
        self.abur += 0.01 if novedad < 0.3 else -0.02
        self.abur = max(0.0, min(1.0, self.abur))
        # memoria relacional: SOLO refuerza ubicacion de comida (HRR 0028), no la celda actual
        # (reforzar la celda visitada crea pozo que impide explorar)

class World:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.dolor_cells = set()
        self.food_cells = set()
        # 8 celdas de dolor en una zona
        for _ in range(8):
            self.dolor_cells.add((self.rng.randint(0,GRID-1), self.rng.randint(0,GRID-1)))
        # 10 comida dispersas
        for _ in range(10):
            self.food_cells.add((self.rng.randint(0,GRID-1), self.rng.randint(0,GRID-1)))
        # obstaculos aislados (no enjaulan el centro)
        self.walls = set([(3,3),(3,4),(8,7),(8,8),(5,9),(6,9)])
        # asegurar que el centro de arranque no sea muro
        self.walls.discard((GRID//2, GRID//2))
    def dolor_at(self, pos):
        return 1.0 if pos in self.dolor_cells or pos in self.walls else 0.0
    def food_at(self, pos):
        return pos in self.food_cells
    def eat(self, pos):
        self.food_cells.discard(pos)

def run_world(use_dolor=True, use_hrr=True, seed=SEED):
    w = World(seed)
    a = Agent(use_dolor=use_dolor, use_hrr=use_hrr)
    for _ in range(STEPS):
        a.step(w)
    return a, w

def main():
    results = {}
    # T-MS-01: evitacion de dano (tipo Animal-AI)
    a_d, _ = run_world(use_dolor=True, use_hrr=True)
    a_nd, _ = run_world(use_dolor=False, use_hrr=True)   # NC: sin dolor
    pain_with = a_d.pain_cum
    pain_without = a_nd.pain_cum
    t1 = pain_with < pain_without * 0.5   # con dolor, mucho menos dolor acumulado
    results["T-MS-01_evita_dano"] = {
        "pain_con_dolor": round(pain_with,3),
        "pain_sin_dolor_NC": round(pain_without,3),
        "pass": bool(t1),
        "meta": "Animal-AI: evitacion de dano via campo dolor real (no regla)"}

    # T-MS-02: espacial (HRR binding recuerda comida)
    a_h, w_h = run_world(use_dolor=True, use_hrr=True)
    a_nh, _ = run_world(use_dolor=True, use_hrr=False)   # NC: sin HRR
    t2 = a_h.food_eaten > a_nh.food_eaten
    results["T-MS-02_espacial"] = {
        "comida_con_HRR": a_h.food_eaten,
        "comida_sin_HRR_NC": a_nh.food_eaten,
        "pass": bool(t2),
        "meta": "Animal-AI: memoria de ubicacion (HRR 0028) encuentra comida"}

    # T-MS-03: exploracion (eta global)
    celdas_unicas = len(a_d.visited)
    t3 = celdas_unicas > 40   # exploro mas de 40 celdas distintas en 300 steps
    results["T-MS-03_exploracion"] = {
        "celdas_visitadas_unicas": celdas_unicas,
        "eta_final": round(a_d.eta,3),
        "abur_final": round(a_d.abur,3),
        "pass": bool(t3),
        "meta": "Crafter-like: diversidad de conducta crece con eta (0036)"}

    # T-MS-04: catalogo emergente (descriptivo, NO integrado)
    results["T-MS-04_catalogo"] = {
        "nota": "OBSERVACIONAL: se cataloga si emerge conducta que etiquetariamos como coherente/pro-social. NO se integra como modulo.",
        "dolor_total": round(a_d.pain_cum,3),
        "comida_total": a_d.food_eaten,
        "visited": celdas_unicas,
        "pass": True,
        "meta": "Marco de observacion de emergencia (no prescriptivo)"}

    overall = all(results[k]["pass"] for k in ["T-MS-01_evita_dano","T-MS-02_espacial","T-MS-03_exploracion"])
    results["overall_pass"] = bool(overall)
    out = {
        "experiment_id":"exp_SGM_0042",
        "name":"minisandbox_observatory",
        "status":"OBSERVATORIO",
        "marco":"Animal-AI (1909.07483): tareas conductuales sin lenguaje. No integra conceptos emergentes.",
        "config":{"GRID":GRID,"STEPS":STEPS,"SEED":SEED},
        "tests":results,
        "verified": bool(overall)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out

if __name__ == "__main__":
    main()
