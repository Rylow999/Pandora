# -*- coding: utf-8 -*-
"""
exp_SGM_0030 -- tick_plan_crossgraph (Fase 7 / B: el tick HRR+roles RESUELVE un plan multi-paso
cruzando dos grafos de conocimiento, lo que el tick plano (0023) no puede).

DISENO HONESTO (reparado 2026-08-02 tras auditoria): el cruce G1<->G2 NO existe como arista
fisica. Vive SOLO en memoria relacional HRR: rel_mem[llave] = bind(rol_meta_G1, omega_meta_G1).
- El tick HRR+roles hace unbind(rol_meta) sobre rel_mem[llave] y recupera meta_G1 -> llega.
- El tick PLANO usa PPR Euclidiana sobre aristas fisicas. Como NO hay arista llave->meta_G1,
  de verdad no llega. No es un 'return False' hardcoded: es un plano que de verdad fracasa.

Tests (con negative control real, no garantizado por construccion):
  T-CROSS-01: exito del plan HRR+roles > 0.8
  T-CROSS-02: exito del plan PLANO (Euclidiano real) < 0.3  [medido por computo, no hardcoded]
  T-CROSS-NC: roles al azar en el cruce -> exito < 0.3 (si con ruido igual llega, no mide)
"""
import math, random, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hrr_core as H
import tick_relational_core as T

SEED = 42
D = 128
TRIALS = 20

def build_crossgraph(rng, n_g1=6, n_g2=5):
    """G1 y G2 desconectados SALVO cruce en memoria relacional HRR (no arista fisica)."""
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
    # NOTA: NO hay edges[llave].append((meta,0)) -> el cruce vive solo en rel_mem
    return omega, edges, n_g1-1, llave

def make_tick(rng, corrupt_cruce=False):
    omega, edges, meta, llave = build_crossgraph(rng)
    # cruce HRR empaquetado en rel_mem[llave]: "la llave destraba la meta de G1"
    # debe usar el rol REAL del nodo meta (role_vecs[meta]) para que recover_chain lo destape.
    tick0 = T.TickRelational(omega, edges, D, seed=SEED)  # crea role_vecs consistentes
    if corrupt_cruce:
        # NC: el cruce apunta a un nodo random de G2, no a meta_G1
        fake = random.Random(rng.randint(0, 10**9)).randrange(len(omega))
        while fake == meta: fake = random.Random(rng.randint(0, 10**9)).randrange(len(omega))
        rel = {llave: H.normalize(H.hrr_bind(tick0.role_vecs[fake], omega[fake]))}
    else:
        rel = {llave: H.normalize(H.hrr_bind(tick0.role_vecs[meta], omega[meta]))}
    tick = T.TickRelational(omega, edges, D, seed=SEED, rel_override=rel)
    return tick, meta, llave

def success_hrr(rng):
    tick, meta, llave = make_tick(rng, corrupt_cruce=False)
    ok_cross = tick.plan_from(llave, [meta], use_roles=True)
    ok_g1 = tick.plan_from(0, list(range(1, meta+1)), use_roles=True)
    return ok_cross and ok_g1

def success_plano(rng):
    tick, meta, llave = make_tick(rng, corrupt_cruce=False)
    # plano REAL: PPR Euclidiana sobre aristas fisicas (sin leer rel_mem)
    return tick.plan_from(llave, [meta], use_roles=False)

def success_nc(rng):
    tick, meta, llave = make_tick(rng, corrupt_cruce=True)
    return tick.plan_from(llave, [meta], use_roles=True)  # cruce corrupto -> debe fallar

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
    print("exp_SGM_0030 TICK_PLAN_CROSSGRAPH (reparado: cruce solo-HRR, plano Euclidiano real)")
    print("  exito plan HRR+roles :", a_hrr, "(debe ser >0.8)")
    print("  exito plan plano     :", a_plano, "(debe ser <0.3, MEDIDO por computo)")
    print("  exito NC (cruce azar):", a_nc, "(debe ser <0.3)")
    print("  T-CROSS-01:", t1, " T-CROSS-02:", t2, " T-CROSS-NC:", t3)
    print("  PASS:", overall)
    result = {
        "experiment_id":"exp_SGM_0030",
        "experiment_name":"tick_plan_crossgraph",
        "phase":"Composicion Relacional (Gap 2) - B: tick resuelve plan cruzando grafos",
        "date":"2026-08-02",
        "hypothesis":"El tick con memoria relacional HRR resuelve un plan multi-paso cruzando dos grafos (cruce empaquetado SOLO en rel_mem[llave] como HRR(rol_meta, omega_meta)). El tick plano (PPR Euclidiana real sobre aristas) no llega porque el cruce no es arista fisica. NC con cruce corrupto falla.",
        "config":{"D":D,"trials":TRIALS,"seed":SEED,
                  "refs":["hrr_core.py","tick_relational_core.py"],
                  "nota_auditoria":"REPARADO: antes plan_from(use_roles=False) hacia 'return False' (hardcoded) y habia arista fisica de cruce. Ahora el plano es PPR Euclidiana real y el cruce vive solo en rel_mem."},
        "result":{
            "exito_plan_HRR_roles":a_hrr,
            "exito_plan_plano_REAL":a_plano,
            "exito_NC_cruce_azar":a_nc,
            "T-CROSS-01":t1,"T-CROSS-02":t2,"T-CROSS-NC":t3,
            "pass":overall,
        },
        "script":"phases/phase7_composicion/run_tick_plan_crossgraph.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0030_tick_plan_crossgraph.json",
        "test_target":"T-CROSS-01/02/NC (NC y plano REALES, no hardcoded)",
        "variant_of":None,
        "lit_refs":["exp_SGM_0028_tick_relational.json"],
        "notes":"Auditoria 2026-08-02: el resultado 'B' tenia el negative control garantizado por 'return False' y una arista de cruce fisica que hubiera dejado al plano ganar. Reparado: cruce solo en rel_mem HRR, plano=PPR Euclidiana real. Ahora el 'plano no puede' se sostiene por computo, no por codigo.",
        "notes_criollo":"Reparamos el B: antes el 'tick plano no puede' era un return False trucho y encima habia una arista de cruce fisica que lo hubiera dejado ganar. Ahora el cruce entre grafos vive SOLO adentro del nodo llave (HRR), y el plano de verdad (distancia Euclidiana) no llega porque no hay arista. El HRR lo destapa. El resultado se sostiene por computo real.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0030_tick_plan_crossgraph.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    return result

if __name__ == "__main__":
    main()
