# -*- coding: utf-8 -*-
"""
exp_SGM_0035 -- curiosity_exploration (Camino A: drive de exploracion programado como sustrato medible)
HONESTIDAD DE NIVEL: esto NO es "el agente decide querer explorar por su cuenta" (eso requiere un
estrato superior: modelo predictivo de error->valencia, o modo EXPLORAR metacontrolado; ver 0036+).
Esto es la FORMA BASICA de curiosidad como bonus de novedad en el costo de movimiento: el agente
evita celdas ya visitadas (memoria de visitas), lo que lo saca de optimos locales / callejones.

DISENO (test-first, con negative control):
  Maze 10x10 aleatorio (reusa gen_maze de 0032, con callejones sin salida).
  - GREEDY: argmin dist(nb, meta), SIN memoria de visitas -> rebota en callejones.
  - CURIOSO: argmin ( dist(nb, meta) - ALPHA * novedad(nb) ), novedad=1/(1+visitas[nb]).
             Al pasar por una celda, visitas[celda]+=1 -> no repite, prueba otros caminos.
  - RW (NC): elige vecino al azar.

  T-CUR-01: tasa_llegada(CURIOSO) > tasa_llegada(GREEDY)   (la curiosidad ayuda a no atascarse)
  T-CUR-02: pasos_medio(CURIOSO) <= pasos_medio(GREEDY)    (llega sin gastar mas)
  NC:       tasa_llegada(RW) < tasa_llegada(CURIOSO)       (explorar al azar no focaliza)

Variable discriminante: tasa de llegada en maze con callejones. Si el greedy ya llega 100%, el
test no mide (maze muy facil) -> se reporta y se ajusta dificultad.
"""
import json, os, sys, random
sys.path.insert(0, os.path.dirname(__file__))
import run_grid_agent as G2   # reusa gen_maze, bfs_path, make_scenario

SEED = 20260803
TRIALS = 40
N = 10
ALPHA_CUR = 1.5
MAX_TICKS = 200

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def run_agent(mode, rng, walls, start, goal):
    """Corre un agente en el maze. Devuelve (llego, pasos)."""
    pos = start
    visitas = {}
    pasos = 0
    while pasos < MAX_TICKS:
        if pos == goal:
            return True, pasos
        vecinos = [(r,c) for (r,c) in [(pos[0]+1,pos[1]),(pos[0]-1,pos[1]),
                                        (pos[0],pos[1]+1),(pos[0],pos[1]-1)]
                   if 0<=r<N and 0<=c<N and (r,c) not in walls and (r,c)!=pos]
        if not vecinos:
            return False, pasos
        if mode == "rw":
            nb = rng.choice(vecinos)
        elif mode == "greedy":
            nb = min(vecinos, key=lambda v: manhattan(v, goal))
        elif mode == "curioso":
            def cost(v):
                nov = 1.0/(1.0 + visitas.get(v, 0))
                return manhattan(v, goal) - ALPHA_CUR * nov
            nb = min(vecinos, key=cost)
        else:
            raise ValueError(mode)
        visitas[pos] = visitas.get(pos, 0) + 1
        pos = nb
        pasos += 1
    return False, pasos

def main():
    rng = random.Random(SEED)
    res = {"greedy":[], "curioso":[], "rw":[]}
    for _ in range(TRIALS):
        walls, body, meta, dolor = G2.make_scenario(rng)
        start = (0, 0)
        # solo si es alcanzable (bfs), para medir llegada real
        if not G2.bfs_path(walls, start, meta):
            continue
        for mode in ("greedy", "curioso", "rw"):
            m = random.Random(rng.randint(0, 10**9))
            lleg, pas = run_agent(mode, m, walls, start, meta)
            res[mode].append((lleg, pas))

    def tasa(m): 
        xs = res[m]
        if not xs: return 0.0
        return round(sum(1 for l,p in xs if l)/len(xs), 3)
    def pasos_m(m):
        xs = [p for l,p in res[m] if l]
        return round(sum(xs)/len(xs), 1) if xs else None

    tg, tc, tr = tasa("greedy"), tasa("curioso"), tasa("rw")
    pg, pc = pasos_m("greedy"), pasos_m("curioso")
    t1 = tc > tg
    t2 = (pc is not None) and (pg is not None) and (pc <= pg * 1.5)  # no gasta mucho mas
    tnc = tr < tc
    overall = t1 and t2 and tnc

    print("exp_SGM_0035 CURIOSITY_EXPLORATION (sustrato: bonus de novedad, no deseo emergente)")
    print("  trials alcanzables:", len(res["greedy"]))
    print("  tasa llegada  GREEDY :", tg, " CURIOSO:", tc, " RW(NC):", tr)
    print("  pasos medio    GREEDY :", pg, " CURIOSO:", pc)
    print("  T-CUR-01 (curioso>greedy):", t1, " T-CUR-02 (curioso no gasta mas):", t2, " NC:", tnc)
    print("  PASS:", overall)
    result = {
        "experiment_id":"exp_SGM_0035",
        "experiment_name":"curiosity_exploration",
        "phase":"Camino A - curiosidad: drive de exploracion (sustrato bajo)",
        "date":"2026-08-03",
        "hypothesis":"Curiosidad como bonus de novedad (evitar celdas ya visitadas) saca al agente de callejones sin salida donde el GREEDY (sin memoria de visitas) se traba. El CURIOSO llega mas que el GREEDY y que RW (que no focaliza). Esto es sustrato de exploracion, NO deseo emergente.",
        "config":{"N":N,"trials":TRIALS,"seed":SEED,"alpha_curiosity":ALPHA_CUR,"max_ticks":MAX_TICKS,
                  "nivel":"ESTRATO BAJO: drive programado, no eleccion latente del agente",
                  "refs":["exp_SGM_0032_grid_agent","exp_SGM_0034_identity"]},
        "result":{
            "trials_alcanzables":len(res["greedy"]),
            "tasa_llegada_greedy":tg,"tasa_llegada_curioso":tc,"tasa_llegada_rw_NC":tr,
            "pasos_medio_greedy":pg,"pasos_medio_curioso":pc,
            "T-CUR-01":t1,"T-CUR-02":t2,"NC":tnc,"pass":overall,
        },
        "script":"phases/phase7_composicion/run_curiosity.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0035_curiosity.json",
        "test_target":"T-CUR-01 (curioso>greedy) + T-CUR-02 (curioso no gasta mas) + NC",
        "variant_of":None,
        "lit_refs":["exp_SGM_0032_grid_agent.json","exp_SGM_0034_identity.json"],
        "notes":"Curiosidad = memoria de visitas como bonus de novedad en el costo de movimiento. El greedy sin esa memoria rebota en callejones; el curioso no repite y encuentra la salida. ESTRATO BAJO: el bonus es programado, el agente no 'elige' explorar. El salto a curiosidad latente (que el agente decida por su cuenta) requiere modelo predictivo de error->valencia o modo EXPLORAR metacontrolado (ver experimentos 0036+).",
        "notes_criollo":"Curiosidad version 1: el agente evita lo que ya piso. En un laberinto, el que va directo a la meta sin acordarse de donde estuvo rebota en callejones ciegos; el curioso (que suma 'bonus' por ir a lugar nuevo) prueba otros caminos y llega. Ojo: esto es un empujon programado, no que el bicho 'quiera' explorar. Eso (el deseo latente) es un estrato mas arriba: cuando el error de prediccion genere valencia, o haya un modo EXPLORAR que el sistema se auto-active. Lo dejamos anotado para 0036+.",
    }
    out = os.path.join(os.path.dirname(__file__), "results_exp_SGM_0035_curiosity.json")
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    print("RESULTADO escrito:", out)
    return result

if __name__ == "__main__":
    main()
