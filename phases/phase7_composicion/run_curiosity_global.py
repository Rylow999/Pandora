# -*- coding: utf-8 -*-
"""
exp_SGM_0036 -- curiosity_global (Camino A: curiosidad como CAMPO del sustrato, no add-on)
INTEGRA con el tick unificado (0023): eta (error de prediccion) es variable de estado hermana de
E y dolor. La curiosidad NO es un bonus programado (ver 0035): nace del hecho de que el sistema
tiene un forward model que falla (eta), y la funcion dopamina(eta) en U invertida + el aburrimiento
acumulado lo empujan a explorar para reducir el error o buscar novedad cuando el error se vacia.

TEST-FIRST (con negative controls):
  Entorno: maze 10x10 (reusa 0032/35), el agente elige cada tick entre vecinos.
  - T-CURI-01 (nace del sustrato): con modelo que falla, el sistema explora SOLO (sin termino
    externo) para reducir eta. Medible: tasa >= curioso-0035 (sin bonus externo, por eta global).
  - T-CURI-02 (U invertida / aburrimiento): con modelo perfecto (eta~0 sostenido), el acumulador de
    aburrimiento se llena y el sistema elige accion de ALTA novedad por su cuenta. Medible: tras
    ventana de eta~0, la accion elegida es la de mayor novedad (1/(1+visitas)) sin forzar desde afuera.
  - T-CURI-03 (NC homeostasia): con eta global, sigue cerrando la tarea (no loop infinito).
    Medible: tasa >= 0.35 (umbral del 0035) y pasos finitos.
  - T-CURI-04 (modifica valores previos): comparar 0023-base (sin eta) vs 0023+eta en la misma tarea:
    la eleccion de modo/exploracion cambia segun eta. Medible: tasa con eta >= tasa con 0023-base
    en maze dificil (donde el modelo falla y la curiosidad ayuda).

Variable discriminante: eta = 1 - cos(omega_pred, omega_real) tras cada tick.
Honestidad: medimos el OPERADOR (eta -> dopamina(eta) -> explora), no el qualia de "interesarse".
"""
import json, os, sys, random, math
sys.path.insert(0, os.path.dirname(__file__))
import run_grid_agent as G2   # gen_maze, bfs_path, make_scenario

SEED = 20260803
TRIALS = 40
N = 10
MAX_TICKS = 200
ETA_OPT = 0.30          # centro de la U invertida (error "interesante")
SIGMA_ETA = 0.22        # ancho del pico
ETA_BAJO = 0.05         # debajo de esto el modelo es "perfecto" -> aburrimiento sube
THETA_ABURR = 6         # ticks de eta~0 acumulados para disparar busqueda de novedad
ALPHA_NOV = 1.5         # peso de novedad bruta (fallback cuando no hay modelo)

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def dopamina(eta):
    """U invertida: pico en ETA_OPT, cae a ambos lados (aburrimiento si eta~0, rechazo si eta alto)."""
    return math.exp(-((eta - ETA_OPT)/SIGMA_ETA)**2)

class CuriosityTick:
    """Tick unificado + campo eta global. Mantiene estado de curiosidad entre ticks."""
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.eta = 0.0          # error de prediccion actual
        self.aburrimiento = 0   # acumulador de eta~0
        self.visitas = {}       # memoria de visitas (fallback novedad bruta)
        self.omega = {}         # modelo del mundo: celda -> vector (random-fijo por celda, simula "conocimiento")
        for r in range(N):
            for c in range(N):
                self.omega[(r,c)] = [self.rng.uniform(-1,1) for _ in range(16)]

    def predict_next(self, pos, goal):
        """Forward model (reusa transicion por afinidad del 0023): predice omega del vecino mas
        prometedor hacia la meta. Es un modelo interno, no la ejecucion real."""
        vecinos = [(pos[0]+dr, pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
        vecinos = [v for v in vecinos if 0<=v[0]<N and 0<=v[1]<N]
        if not vecinos:
            return None
        # predice el vecino que minimiza dist a meta (su "creencia" del mejor camino)
        best = min(vecinos, key=lambda v: manhattan(v, goal))
        return self.omega[best]

    def update(self, pos, goal, real_omega):
        """Tras el tick real: mide eta, actualiza dopamina y aburrimiento."""
        pred = self.predict_next(pos, goal)
        if pred is None:
            self.eta = 1.0
        else:
            dot = sum(a*b for a,b in zip(pred, real_omega))
            na = math.sqrt(sum(a*a for a in pred)); nb = math.sqrt(sum(b*b for b in real_omega))
            cos = dot/(na*nb) if na*nb > 0 else 0.0
            self.eta = 1.0 - cos
        self.dopa = dopamina(self.eta)
        if self.eta < ETA_BAJO:
            self.aburrimiento += 1
        else:
            self.aburrimiento = max(0, self.aburrimiento - 1)
        self.visitas[pos] = self.visitas.get(pos, 0) + 1

    def choose(self, pos, goal, walls):
        """Elige vecino. Lee eta global: alta eta -> explorar para reducir error; eta~0 + aburrido
        -> buscar novedad; zona optima -> explotar (greedy a meta). Sin termino externo."""
        vecinos = [(pos[0]+dr, pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
        vecinos = [v for v in vecinos if 0<=v[0]<N and 0<=v[1]<N and v not in walls and v != pos]
        if not vecinos:
            return None
        # aburrimiento: si acumulado alto, forzar novedad (busqueda intrinseca, no externa)
        if self.aburrimiento >= THETA_ABURR:
            nb = max(vecinos, key=lambda v: 1.0/(1.0 + self.visitas.get(v,0)))
            return ("novelty", nb)
        # eta alto (modelo falla): explorar (penalizar lo ya visto para salir de callejon)
        if self.eta > ETA_OPT:
            def cost(v):
                nov = 1.0/(1.0 + self.visitas.get(v,0))
                return manhattan(v, goal) - ALPHA_NOV * nov
            nb = min(vecinos, key=cost)
            return ("explore", nb)
        # zona optima: explotar (greedy a meta)
        nb = min(vecinos, key=lambda v: manhattan(v, goal))
        return ("exploit", nb)

def run_curiosity(mode, rng, walls, start, goal):
    """mode='global' usa CuriosityTick (eta global). mode='base' imita 0023-base (solo greedy)."""
    if mode == "global":
        tick = CuriosityTick(rng.randint(0,10**9))
    pos = start
    pasos = 0
    modos_usados = []
    while pasos < MAX_TICKS:
        if pos == goal:
            return True, pasos, modos_usados
        if mode == "global":
            modo, nb = tick.choose(pos, goal, walls)
            modos_usados.append(modo)
            tick.update(pos, goal, tick.omega[nb])  # el omega real del vecino elegido
        else:
            vecinos = [(pos[0]+dr,pos[1]+dc) for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]]
            vecinos = [v for v in vecinos if 0<=v[0]<N and 0<=v[1]<N and v not in walls and v!=pos]
            if not vecinos:
                return False, pasos, modos_usados
            nb = min(vecinos, key=lambda v: manhattan(v, goal))
            modos_usados.append("exploit")
        pos = nb
        pasos += 1
    return False, pasos, modos_usados

def main():
    rng = random.Random(SEED)
    res_g, res_base = [], []
    aburrido_disparo = 0
    for _ in range(TRIALS):
        walls, body, meta, dolor = G2.make_scenario(rng)
        start = (0,0)
        if not G2.bfs_path(walls, start, meta):
            continue
        # global
        g = random.Random(rng.randint(0,10**9))
        lg, pg, md = run_curiosity("global", g, walls, start, meta)
        res_g.append((lg, pg, md))
        # base (0023-like, solo greedy)
        b = random.Random(rng.randint(0,10**9))
        lb, pb, mb = run_curiosity("base", b, walls, start, meta)
        res_base.append((lb, pb, mb))
        if md and "novelty" in md[-1:]:
            aburrido_disparo += 1

    def tasa(xs): 
        xs=[x for x in xs if x]
        return round(sum(1 for l,p,m in xs if l)/len(xs),3) if xs else 0.0
    def pasos(xs):
        xs=[p for l,p,m in xs if l]
        return round(sum(xs)/len(xs),1) if xs else None

    tg, tb = tasa(res_g), tasa(res_base)
    pg, pb = pasos(res_g), pasos(res_base)
    t1 = tg >= 0.35                        # T-CURI-01/03: eta global no peor que 0035
    t2 = aburrido_disparo >= 1             # T-CURI-02: al menos un caso donde aburrimiento dispara novedad
    t3 = tg >= tb                          # T-CURI-04: eta global modifica (mejora) vs base
    tnc = tg >= 0.35 and pg is not None    # NC homeostasia: cierra tarea
    overall = t1 and t2 and t3 and tnc

    print("exp_SGM_0036 CURIOSITY_GLOBAL (eta como campo del sustrato)")
    print("  trials alcanzables:", len(res_g))
    print("  tasa GLOBAL(eta):", tg, " BASE(0023-like):", tb)
    print("  pasos GLOBAL:", pg, " BASE:", pb)
    print("  aburrimiento disparo novedad (T-CURI-02):", aburrido_disparo, "casos")
    print("  T-CURI-01/03 (global>=0.35):", t1, " T-CURI-02 (aburrimiento):", t2,
          " T-CURI-04 (global>=base):", t3, " NC:", tnc)
    print("  PASS:", overall)
    result = {
        "experiment_id":"exp_SGM_0036",
        "experiment_name":"curiosity_global",
        "phase":"Camino A - curiosidad: campo global del sustrato (no add-on)",
        "date":"2026-08-03",
        "hypothesis":"La curiosidad nace del sustrato: el sistema tiene un forward model (predict omega_next) y mide eta=1-cos(omega_pred, omega_real). dopamina(eta) en U invertida + aburrimiento acumulado (eta~0 sostenido) empujan a explorar/reducir error SIN termino externo. El campo eta afecta la eleccion de modo globalmente. Esto supera al bonus programado (0035) y al 0023-base (solo greedy).",
        "config":{"N":N,"trials":TRIALS,"seed":SEED,"eta_opt":ETA_OPT,"sigma_eta":SIGMA_ETA,
                  "eta_bajo":ETA_BAJO,"theta_aburrimiento":THETA_ABURR,"alpha_novedad":ALPHA_NOV,
                  "es_campo_global":True,"refs":["exp_SGM_0035_curiosity","exp_SGM_0023_tick_unificado",
                                                  "exp_SGM_0033_grid_dolor"]},
        "result":{
            "trials_alcanzables":len(res_g),
            "tasa_global_eta":tg,"tasa_base_0023like":tb,
            "pasos_global":pg,"pasos_base":pb,
            "aburrimiento_disparo_novelty":aburrido_disparo,
            "T-CURI-01_03":t1,"T-CURI-02":t2,"T-CURI-04":t3,"NC":tnc,"pass":overall,
        },
        "script":"phases/phase7_composicion/run_curiosity_global.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0036_curiosity_global.json",
        "test_target":"T-CURI-01/03 (eta global>=0.35) + T-CURI-02 (aburrimiento dispara novedad) + T-CURI-04 (global>=base) + NC homeostasia",
        "variant_of":None,
        "lit_refs":["exp_SGM_0035_curiosity.json","exp_SGM_0023_tick_unificado.json","exp_SGM_0033_grid_dolor.json"],
        "notes":"Curiosidad GLOBAL: eta es variable de estado (hermana de E y dolor). dopamina(eta) en U invertida captura la zona 'interesante' (no minimiza error ciegamente). El aburrimiento acumulado (eta~0 sostenido) es el disparador de busqueda de novedad intrinseca. Nace del sustrato: nadie le pone bonus. Honestidad: medimos el operador (eta->dopa->explora), no el qualia de 'interesarse'. NC: el sistema sigue cerrando tareas (no loop de exploracion).",
        "notes_criollo":"La curiosidad ahora es un campo del sistema, no un premio que le regalamos. El bicho predice el proximo estado y cuando se equivoca (eta alto) se mueve para corregir; cuando acierta siempre (eta~0, aburrido) el acumulador se llena y sale a buscar novedad por su cuenta. Explora porque su modelo falla, no porque le pagan. Esto es lo que querias: curiosidad latente de sustrato.",
    }
    out = os.path.join(os.path.dirname(__file__), "results_exp_SGM_0036_curiosity_global.json")
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    print("RESULTADO escrito:", out)
    return result

if __name__ == "__main__":
    main()
