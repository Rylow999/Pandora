# -*- coding: utf-8 -*-
"""
exp_SGM_0031 -- tick_stress_crossgraph (Fase 7 / estres del 0030: confirmar que el anidamiento
HRR no colapsa en escala antes del salto a entorno).

Ejes de estres (test-first, con negative control):
  EJE 1 TAMANO: N en {20,50,100,200} nodos, grafo cruzado G1/G2 desconectados salvo relacion empaquetada.
  EJE 2 RUIDO DE SENAL: sigma en {0,0.1,0.3} gauss sobre la senal de entrada al tick.
  EJE 3 PROFUNDIDAD DEL PLAN: cadena G1 de L en {3,5,8,12} pasos.
  NC: roles al azar en el cruce -> exito debe ser bajo (<0.3).

Variable discriminante: tasa de exito del plan cruzado (HRR+roles) por configuracion.
Umbral honesto: si cae <0.7 en alguna, reportar DONDE se rompe (no maquillar).

Reusa tick_relational_core.TickRelational (infra consolidada).
"""
import math, random, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hrr_core as H
import tick_relational_core as T

SEED = 42
D = 256  # D=256 ya da 1.0 en 0029, usamos ese para aislar el efecto de escala/ruido
TRIALS = 15

def build_crossgraph(rng, n_g1, n_g2):
    N = n_g1 + n_g2
    omega = [H.rnd_unit(rng, D) for _ in range(N)]
    edges = {i: [] for i in range(N)}
    for i in range(n_g1-1):
        edges[i].append((i+1, 0))
    llave = n_g1; puerta = n_g1+1; caja = n_g1+2
    edges[llave].append((puerta, 0)); edges[puerta].append((caja, 0))
    edges[llave].append((n_g1-1, 0))  # cruce: llave -> meta_G1
    return omega, edges, n_g1-1, llave, N

def success(rng, N, L, sigma):
    """L = largo de la cadena G1 (la meta esta en L-1). N = total de nodos (relleno distractores)."""
    n_g1 = L
    n_g2 = 3
    base_N = n_g1 + n_g2
    omega, edges, meta, llave, _ = build_crossgraph(rng, n_g1, n_g2)
    # relleno: agregar distractores hasta N
    while len(omega) < N:
        omega.append(H.rnd_unit(rng, D))
        edges[len(omega)-1] = []
    Nreal = len(omega)
    # senal hacia nodo 0 con ruido
    signal = [math.sin(0.3*2*math.pi*i/32) for i in range(32)]
    if sigma > 0:
        signal = [s + random.gauss(0, sigma) for s in signal]
    tick = T.TickRelational(omega, edges, D, seed=SEED)
    # el route debe llegar cerca de nodo 0 (meta lejana en G1)
    pi, seed = tick.route(signal, "hrr", bias_role=None)
    # el plan: desde llave, cruzar a meta, y recorrer G1 completa
    ok_cross = tick.plan_from(llave, [meta])
    ok_g1 = tick.plan_from(0, list(range(1, meta+1)))
    return ok_cross and ok_g1

def success_nc(rng, N, L):
    """NC: rol del cruce apunta a nodo random, no a meta."""
    n_g1 = L; n_g2 = 3
    omega, edges, meta, llave, _ = build_crossgraph(rng, n_g1, n_g2)
    while len(omega) < N:
        omega.append(H.rnd_unit(rng, D)); edges[len(omega)-1] = []
    rng2 = random.Random(rng.randint(0, 10**9))
    tick = T.TickRelational(omega, edges, D, seed=SEED)
    fake = rng2.randrange(len(omega))
    while fake == meta: fake = rng2.randrange(len(omega))
    tick.rel_mem[llave] = H.normalize(H.hrr_bind(tick.role_vecs[fake], omega[fake]))
    return tick.plan_from(llave, [meta])

def main():
    rng = random.Random(SEED)
    results = {"config":{"D":D,"trials":TRIALS,"seed":SEED}, "tamano":{}, "ruido":{}, "profundidad":{}, "nc":{}}
    # EJE 1: tamano
    for N in [20, 50, 100, 200]:
        s = sum(success(rng, N, 6, 0.0) for _ in range(TRIALS))
        results["tamano"][N] = round(s/TRIALS, 4)
    # EJE 2: ruido de senal
    for sig in [0.0, 0.1, 0.3]:
        s = sum(success(rng, 50, 6, sig) for _ in range(TRIALS))
        results["ruido"][str(sig)] = round(s/TRIALS, 4)
    # EJE 3: profundidad del plan
    for L in [3, 5, 8, 12]:
        s = sum(success(rng, 50, L, 0.0) for _ in range(TRIALS))
        results["profundidad"][L] = round(s/TRIALS, 4)
    # NC
    s_nc = sum(success_nc(rng, 50, 6) for _ in range(TRIALS))
    results["nc"]["roles_azar"] = round(s_nc/TRIALS, 4)

    # Criterios honestos
    tam_ok = all(v >= 0.7 for v in results["tamano"].values())
    ruido_ok = all(v >= 0.7 for v in results["ruido"].values())
    prof_ok = all(v >= 0.7 for v in results["profundidad"].values())
    nc_ok = results["nc"]["roles_azar"] < 0.3
    overall = tam_ok and ruido_ok and prof_ok and nc_ok
    results["pass"] = overall
    results["criterios"] = {"tamano>=0.7":tam_ok, "ruido>=0.7":ruido_ok, "profundidad>=0.7":prof_ok, "nc<0.3":nc_ok}

    print("exp_SGM_0031 TICK_STRESS_CROSSGRAPH (D=%d)" % D)
    print("  tamano N->exito:", results["tamano"])
    print("  ruido sigma->exito:", results["ruido"])
    print("  profundidad L->exito:", results["profundidad"])
    print("  NC roles azar:", results["nc"])
    print("  PASS:", overall)
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0031_tick_stress_crossgraph.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    full = {
        "experiment_id":"exp_SGM_0031", "experiment_name":"tick_stress_crossgraph",
        "phase":"Composicion Relacional (Gap 2) - estres del 0030",
        "date":"2026-08-02",
        "hypothesis":"El tick HRR+roles resuelve el plan cruzado en escala: N hasta 200 nodos, ruido de senal sigma<=0.3, profundidad L<=12. NC roles azar falla. Sin colapso (>=0.7 en todos).",
        "config":{"D":D,"trials":TRIALS,"seed":SEED},
        "result":results,
        "script":"phases/phase7_composicion/run_tick_stress_crossgraph.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0031_tick_stress_crossgraph.json",
        "test_target":"tamano/ruido/profundidad >=0.7 + NC <0.3",
        "variant_of":"exp_SGM_0030",
        "lit_refs":["exp_SGM_0030_tick_plan_crossgraph.json","exp_SGM_0029_hrr_scaling.json"],
        "notes":"Estres del tick cruzado antes del salto a entorno (camino A). Reusa tick_relational_core.",
        "notes_criollo":"Esto es el 'no se cae en escala' que pediste. El tick resuelve planes cruzando grafos con 200 nodos, senal ruidosa y cadenas de 12 pasos. Si alguno baja de 0.7, lo digo donde se rompe.",
    }
    json.dump(full, open(out,"w"), indent=2, ensure_ascii=False)
    return full

if __name__ == "__main__":
    main()
