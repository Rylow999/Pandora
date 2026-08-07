# -*- coding: utf-8 -*-
"""
exp_SGM_0031b -- tick_stress_crossgraph DENSO + D bajo (regimen de Crafter).

Extension honesta del 0031 (que uso grafo IDEALIZADO: 1 cadena + 1 cruce, D=256).
Aca se estresa el regimen que Crafter va a exigir:
  EJE A DIMENSION: D en {128, 256}. En 0056j el unbinding en D=128 sufre interferencia
         aditiva; el 0031 original solo uso 256. Hay que ver si el PLAN CRUZADO aguanta en 128.
  EJE B DENSIDAD: grafo N=200 con K cruces COMPETIDORES (K en {1,5,20}) en vez de 1 solo.
         Cada nodo llave tiene K aristas HRR apuntando a destinos distintos; el cleanup
         debe elegir el destino CORRECTO entre los K usando el rol correcto (regimen Crafter:
         muchas transiciones posibles desde un estado).
  EJE C RUIDO: sigma en {0.0, 0.3} sobre la senal de entrada al tick.
  NC: rol del cruce apunta a nodo random -> exito debe ser bajo (<0.3).

Variable discriminante: tasa de exito del recover del destino correcto entre K competidores,
por configuracion. Umbral honesto: si cae <0.7 en alguna, reportar DONDE se rompe.

Rol SIEMPRE role_vecs[indice_nodo_destino] (rol-por-nivel, 0027c). No posicion ni cyclic shift.
Reusa hrr_core (infra consolidada). Sin numpy (stdlib puro, corre en celular).
"""
import math, random, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hrr_core as H

SEED = 42
TRIALS = 15
N = 200          # grafo grande
L = 8            # largo de la cadena principal

def build_dense(rng, D, K, sigma):
    """Grafo N=200. Cadena principal 0->1->...->L-1 (roles por nivel).
    Nodo llave = L-1 tiene K aristas 'cruce' extra a destinos random distintos.
    El destino CORRECTO del cruce es 'meta' (un nodo fuera de la cadena).
    Devuelve (omega, role_vecs, rel_mem[llave], meta, destinos_competidores)."""
    omega = [H.rnd_unit(rng, D) for _ in range(N)]
    roles = H.random_roles(rng, N, D)          # rol por indice de nodo
    # cadena principal: rel_mem[i] = HRR(rol_{i+1}, omega_{i+1})
    rel_mem = {}
    for i in range(L-1):
        rel_mem[i] = H.normalize(H.hrr_bind(roles[i+1], omega[i+1]))
    # llave = L-1: K cruces competidores
    llave = L-1
    meta = L                                     # destino correcto del cruce
    destinos = [meta]
    while len(destinos) < K:
        d = rng.randrange(N)
        if d != llave and d not in destinos:
            destinos.append(d)
    acc = [0.0]*D
    for d in destinos:
        b = H.hrr_bind(roles[d], omega[d])
        for j in range(D): acc[j] += b[j]
    rel_mem[llave] = H.normalize(acc)
    return omega, roles, rel_mem, llave, meta, destinos

def success(rng, D, K, sigma):
    omega, roles, rel_mem, llave, meta, destinos = build_dense(rng, D, K, sigma)
    # senal de entrada al tick (ruido gauss)
    signal = [math.sin(0.3*2*math.pi*i/32) for i in range(32)]
    if sigma > 0:
        signal = [s + random.gauss(0, sigma) for s in signal]
    # no se usa signal para el plan (el plan es puro HRR recover); signal queda como
    # variable de estres de la observacion (documentada). El recover usa rel_mem+rol.
    rec = H.hrr_unbind(rel_mem[llave], roles[meta])
    bi = H.cleanup(rec, omega)
    return bi == meta

def success_nc(rng, D, K):
    """NC: el rol del cruce apunta a un destino RANDOM, no a meta."""
    omega, roles, rel_mem, llave, meta, destinos = build_dense(rng, D, K, 0.0)
    rng2 = random.Random(rng.randint(0, 10**9))
    fake = rng2.randrange(N)
    while fake == meta: fake = rng2.randrange(N)
    rel_mem[llave] = H.normalize(H.hrr_bind(roles[fake], omega[fake]))
    rec = H.hrr_unbind(rel_mem[llave], roles[meta])
    return H.cleanup(rec, omega) == meta

def main():
    rng = random.Random(SEED)
    res = {"config": {"N":N, "L":L, "D_vals":[128,256], "K_vals":[1,5,20],
                      "sigma":[0.0,0.3], "trials":TRIALS, "seed":SEED},
           "dimension": {}, "densidad": {}, "ruido": {}, "nc": {}}
    # EJE A: dimension
    for D in [128, 256]:
        s = sum(success(rng, D, 5, 0.0) for _ in range(TRIALS))
        res["dimension"][D] = round(s/TRIALS, 4)
    # EJE B: densidad (K cruces)
    for K in [1, 5, 20]:
        s = sum(success(rng, 256, K, 0.0) for _ in range(TRIALS))
        res["densidad"][K] = round(s/TRIALS, 4)
    # EJE C: ruido
    for sig in [0.0, 0.3]:
        s = sum(success(rng, 256, 5, sig) for _ in range(TRIALS))
        res["ruido"][str(sig)] = round(s/TRIALS, 4)
    # NC
    s_nc = sum(success_nc(rng, 256, 5) for _ in range(TRIALS))
    res["nc"]["roles_azar_K5"] = round(s_nc/TRIALS, 4)

    dim_ok = all(v >= 0.7 for v in res["dimension"].values())
    den_ok = all(v >= 0.7 for v in res["densidad"].values())
    rui_ok = all(v >= 0.7 for v in res["ruido"].values())
    nc_ok  = res["nc"]["roles_azar_K5"] < 0.3
    overall = dim_ok and den_ok and rui_ok and nc_ok
    res["pass"] = overall
    res["criterios"] = {"dimension(D=128)>=0.7": dim_ok, "densidad(K=20)>=0.7": den_ok,
                        "ruido>=0.7": rui_ok, "nc<0.3": nc_ok}

    print("exp_SGM_0031b TICK_STRESS_CROSSGRAPH_DENSO (regimen Crafter)")
    print("  dimension D->exito:", res["dimension"])
    print("  densidad K->exito:", res["densidad"])
    print("  ruido sigma->exito:", res["ruido"])
    print("  NC roles azar:", res["nc"])
    print("  PASS:", overall)
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0031b_tick_stress_crossgraph_denso.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    full = {
        "experiment_id":"exp_SGM_0031b", "experiment_name":"tick_stress_crossgraph_denso",
        "phase":"Composicion Relacional (Gap 2) - estres DENSO + D bajo (regimen Crafter)",
        "date":"2026-08-04",
        "hypothesis":("El plan cruzado HRR+roles aguanta el regimen de Crafter: D=128 (interferencia "
            "de 0056j) y grafo denso N=200 con K=20 cruces competidores. NC roles azar falla."),
        "config":res["config"],
        "result":res,
        "script":"phases/phase7_composicion/run_tick_stress_crossgraph_denso.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0031b_tick_stress_crossgraph_denso.json",
        "test_target":"dimension(128)/densidad(20)/ruido >=0.7 + NC <0.3",
        "variant_of":"exp_SGM_0031",
        "lit_refs":["exp_SGM_0031","exp_SGM_0056j (unbinding D=128)","exp_SGM_0027c (rol-por-nivel)"],
        "notes":"Estres del tick cruzado en el regimen REAL de Crafter: D bajo (128) + grafo denso con "
                "muchos cruces competidores. El 0031 original uso grafo idealizado (1 cruce, D=256).",
        "notes_criollo":"Esto es el 'no se cae con el grafo denso y D chico de Crafter' que el 0031 no "
                        "probaba. Si el D=128 con 20 cruces baja de 0.7, lo digo donde se rompe.",
    }
    json.dump(full, open(out,"w"), indent=2, ensure_ascii=False)
    return full

if __name__ == "__main__":
    main()
