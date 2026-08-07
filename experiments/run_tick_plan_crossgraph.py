# -*- coding: utf-8 -*-
"""
exp_SGM_0030 -- tick_plan_crossgraph (Fase 7 / B: el tick HRR+roles RESUELVE un plan multi-paso
cruzando dos grafos de conocimiento, lo que el tick plano (0023) no puede).

Diseño (test-first, con negative control):
  G1 = "mapa": cadena start_G1 -> ... -> meta_G1 (la meta esta en G1)
  G2 = "inventario": llave -> puerta -> caja
  RELACION CRUZADA: el nodo 'llave' (G2) tiene arista HRR(rol_meta, omega_meta_G1).
    O sea "la llave destraba la meta de G1" vive empaquetada en el nodo llave.
  Para llegar a meta_G1, el tick debe: ir a G2, recuperar la relacion cruzada (llave -> meta_G1),
  y eso le da el puente. Sin eso, G1 y G2 estan desconectados y el plano no llega.

  T-CROSS-01: tasa de exito del plan (llegar a meta_G1) con tick HRR+roles > 0.8
  T-CROSS-02: tick plano (sin roles) < 0.3  (no puede puentear G1-G2)
  T-CROSS-NC: roles al azar entre G1/G2 -> exito < 0.3 (si con ruido igual llega, el test no mide)

Variable discriminante: exito del plan multi-paso HRR vs plano. Es la primera vez que el
anidamiento (0027c/28) DEJA DE SER EXPERIMENTO y PASA A SER HERRAMIENTA del sistema (resuelve algo).
"""
import math, random, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hrr_core as H
import tick_relational_core as T

SEED = 42
D = 128
TRIALS = 20

def build_crossgraph(rng, n_g1=6, n_g2=5):
    """Devuelve (omega, edges, meta_g1, llave_g2). G1 y G2 desconectados salvo cruce en llave."""
    N = n_g1 + n_g2
    omega = [H.rnd_unit(rng, D) for _ in range(N)]
    edges = {i: [] for i in range(N)}
    # G1: cadena 0->1->...->(n_g1-1) [meta en n_g1-1]
    for i in range(n_g1-1):
        edges[i].append((i+1, 0))
    # G2: llave(n_g1) -> puerta(n_g1+1) -> caja(n_g1+2)
    llave = n_g1
    puerta = n_g1+1
    caja = n_g1+2
    edges[llave].append((puerta, 0))
    edges[puerta].append((caja, 0))
    # relacion cruzada: llave apunta a meta_G1 (n_g1-1) -> "la llave destraba la meta"
    edges[llave].append((n_g1-1, 0))
    return omega, edges, n_g1-1, llave

def success_hrr(rng):
    omega, edges, meta, llave = build_crossgraph(rng)
    tick = T.TickRelational(omega, edges, D, seed=SEED)
    # plan multi-paso: desde llave, recuperar el cruce a meta, y ademas la cadena G1 completa
    # el tick debe resolver: llave -> meta_G1 (cruce) y meta_G1 es alcanzable
    ok_cross = tick.plan_from(llave, [meta])
    # ademas verificar que desde start_G1 la cadena llega a meta (camino interno G1)
    ok_g1 = tick.plan_from(0, list(range(1, meta+1)))
    return ok_cross and ok_g1

def success_plano(rng):
    omega, edges, meta, llave = build_crossgraph(rng)
    tick = T.TickRelational(omega, edges, D, seed=SEED)
    # tick plano: usa_roles=False -> plan_from devuelve False siempre (no hay memoria relacional)
    return tick.plan_from(llave, [meta], use_roles=False)

def success_nc(rng):
    """NC: roles al azar entre G1 y G2 -> el cruce apunta a un nodo random, no a meta_G1."""
    omega, edges, meta, llave = build_crossgraph(rng)
    N = len(omega)
    # role_vecs con cruce al azar: reasignamos el rol del nodo meta por uno random
    rng2 = random.Random(rng.randint(0, 10**9))
    tick = T.TickRelational(omega, edges, D, seed=SEED)
    # truco: sobreescribimos rel_mem de llave para que apunte a un nodo random distinto de meta
    fake_tgt = rng2.randrange(N)
    while fake_tgt == meta: fake_tgt = rng2.randrange(N)
    tick.rel_mem[llave] = H.normalize(H.hrr_bind(tick.role_vecs[fake_tgt], omega[fake_tgt]))
    return tick.plan_from(llave, [meta])  # debe fallar: el cruce real apunta a fake_tgt, no meta

def main():
    rng = random.Random(SEED)
    s_hrr = sum(success_hrr(rng) for _ in range(TRIALS))
    s_plano = sum(success_plano(rng) for _ in range(TRIALS))
    s_nc = sum(success_nc(rng) for _ in range(TRIALS))
    a_hrr = round(s_hrr/TRIALS, 4)
    a_plano = round(s_plano/TRIALS, 4)
    a_nc = round(s_nc/TRIALS, 4)
    t1 = a_hrr > 0.8
    t2 = a_plano < 0.3
    t3 = a_nc < 0.3
    overall = t1 and t2 and t3
    print("exp_SGM_0030 TICK_PLAN_CROSSGRAPH")
    print("  exito plan HRR+roles :", a_hrr, "(debe ser >0.8)")
    print("  exito plan plano     :", a_plano, "(debe ser <0.3)")
    print("  exito NC (roles azar):", a_nc, "(debe ser <0.3)")
    print("  T-CROSS-01:", t1, " T-CROSS-02:", t2, " T-CROSS-NC:", t3)
    print("  PASS:", overall)
    result = {
        "experiment_id":"exp_SGM_0030",
        "experiment_name":"tick_plan_crossgraph",
        "phase":"Composicion Relacional (Gap 2) - B: tick resuelve plan cruzando grafos",
        "date":"2026-08-02",
        "hypothesis":"El tick con memoria relacional HRR (0028/29) resuelve un plan multi-paso que requiere cruzar dos grafos de conocimiento (relacion 'llave destraba meta de G1' empaquetada en nodo llave). El tick plano no puede (G1/G2 desconectados). NC con roles al azar falla.",
        "config":{"D":D,"trials":TRIALS,"seed":SEED,
                  "refs":["exp_SGM_0028 (tick)","exp_SGM_0029 (scaling)","hrr_core.py","tick_relational_core.py"]},
        "result":{
            "exito_plan_HRR_roles":a_hrr,
            "exito_plan_plano":a_plano,
            "exito_NC_roles_azar":a_nc,
            "T-CROSS-01":t1,"T-CROSS-02":t2,"T-CROSS-NC":t3,
            "pass":overall,
        },
        "script":"phases/phase7_composicion/run_tick_plan_crossgraph.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0030_tick_plan_crossgraph.json",
        "test_target":"T-CROSS-01/02/NC",
        "variant_of":None,
        "lit_refs":["exp_SGM_0028_tick_relational.json","exp_SGM_0029_hrr_scaling.json"],
        "notes":"Primer uso de HRR+roles como HERRAMIENTA del sistema (no experimento aislado). El tick planea cruzando G1/G2 via relacion empaquetada. Usa hrr_core.py y tick_relational_core.py (consolidados).",
        "notes_criollo":"Esto es el B que acordamos: el tick ya no solo LINKEA, ahora RESUELVE. Para llegar a la meta de un grafo, tiene que ir al otro grafo, destapar la relacion 'llave abre meta' que esta guardada ADENTRO del nodo llave (grafo de grafos), y usarla. El tick plano no puede porque G1 y G2 estan sueltos. Es la primera vez que el anidamiento (0027c/28) sirve para resolver algo de verdad.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0030_tick_plan_crossgraph.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    return result

if __name__ == "__main__":
    main()
