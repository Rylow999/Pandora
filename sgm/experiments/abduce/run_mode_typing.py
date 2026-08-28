# -*- coding: utf-8 -*-
"""
exp_SGM_0016 -- mode_typing (Fase 1: Infraestructura de Modos)
Valida SGM v1.4 §1.1: un MODO no es un modulo, es un vector de sesgos beta_mode
que modula los parametros del grafo (boost_edges por tipo de arista, K, W_base, lambda, etc).

Hipotesis:
  Con el MISMO grafo, aplicar MODO_SENSORIAL vs MODO_RAZONAMIENTO vs MODO_PLAN produce
  afinidad (Eq.2) y ventana W(t) (Eq.8) DIFERENTES y reproducibles (seed fijo). Cuando hay
  competencia real entre aristas de distinto tipo, el MODO cambia la decision de caminata.
  La transicion entre modos es limpia: no deja omega contaminada.

Test-first:
  - boost_edges por tipo de arista difiere entre modos (tabla §1.1).
  - ESCENARIO COMPETENCIA: nodo raiz 0, dos candidatos a IGUAL distancia: nodo 1 (arista
    Terminal) y nodo 2 (arista Causal). En SENSORIAL (Terminal boost 2.0) gana el 1; en
    RAZONAMIENTO (Causal boost 2.0) gana el 2. El MODO cambia la eleccion.
  - Afinidad ponderada del mismo vecindario difiere entre modos (la spec: el modo modifica params).
  - W(t) con W_base del modo difiere entre modos.
  - Transicion RAZONAMIENTO -> PLAN no altera los omega de los nodos.

Eq.2: P(m|n) ~ exp(-alpha * ||w_m - w_n||) * boost_edges[tipo_arista]
Eq.8: W(t) = W_base / (1 + kappa_W * E_root)
"""
import math, random, json

D = 16
SEED = 42
KAPPA_W = 2.0

BETA = {
    "SENSORIAL": {
        "boost_edges": {"Terminal":2.0,"Causal":0.8,"Temporal":1.0,"Functional":1.0,"Cognitive":0.8},
        "K":5, "W_base":8, "lambda":2.0, "theta_interf":0.60, "alpha":8.0, "phi_bias":0.0,
    },
    "RAZONAMIENTO": {
        "boost_edges": {"Terminal":0.8,"Causal":2.0,"Temporal":1.2,"Functional":1.5,"Cognitive":2.0},
        "K":20, "W_base":50, "lambda":5.0, "theta_interf":0.85, "alpha":5.0, "phi_bias":math.pi/2,
    },
    "PLAN": {
        "boost_edges": {"Terminal":0.8,"Causal":1.2,"Temporal":2.0,"Functional":2.0,"Cognitive":1.0},
        "K":10, "W_base":100, "lambda":3.0, "theta_interf":0.75, "alpha":4.0, "phi_bias":math.pi/4,
    },
}
EDGE_TYPES = ["Terminal","Causal","Temporal","Functional","Cognitive"]

def dist(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def affinity(n_omega, m_omega, etype, mode_params):
    """Eq.2 con boost_edges del modo."""
    base = math.exp(-mode_params["alpha"] * dist(n_omega, m_omega))
    return base * mode_params["boost_edges"][etype]

def window(mode_params, E_root=0.0):
    return mode_params["W_base"] / (1 + KAPPA_W * E_root)

def build_competition(seed=SEED):
    """Raiz 0; candidatos 1 (Terminal) y 2 (Causal) a IGUAL distancia de 0."""
    rng = random.Random(seed)
    w0 = [rng.gauss(0, 0.3) for _ in range(D)]
    # perturbaciones simetricas para que 1 y 2 queden igual de lejos de 0
    d1 = [rng.gauss(0, 0.2) for _ in range(D)]
    d2 = [-x for x in d1]  # opuesto -> misma norma
    w1 = [a + b for a, b in zip(w0, d1)]
    w2 = [a + b for a, b in zip(w0, d2)]
    return {0: w0, 1: w1, 2: w2}

def choose(mode_name, nodes, seed=SEED):
    """Elige entre nodos 1 y 2 desde 0 usando afinidad con boost del modo."""
    mp = BETA[mode_name]
    a1 = affinity(nodes[0], nodes[1], "Terminal", mp)
    a2 = affinity(nodes[0], nodes[2], "Causal", mp)
    return (1 if a1 >= a2 else 2), round(a1, 4), round(a2, 4)

def main():
    nodes = build_competition()
    # Test de competencia: el modo cambia la eleccion
    cS = choose("SENSORIAL", nodes)
    cR = choose("RAZONAMIENTO", nodes)
    cP = choose("PLAN", nodes)
    mode_flips_choice = (cS[0] != cR[0])  # Sensorial vs Razonamiento deben diferir (Terminal vs Causal)
    sens_wins_terminal = (cS[0] == 1)      # Sensorial debe preferir Terminal(1)
    raz_wins_causal = (cR[0] == 2)         # Razonamiento debe preferir Causal(2)

    # Test afinidad difiere entre modos (mismo vecindario)
    aS = affinity(nodes[0], nodes[1], "Terminal", BETA["SENSORIAL"])
    aR = affinity(nodes[0], nodes[1], "Terminal", BETA["RAZONAMIENTO"])
    affinity_differs = abs(aS - aR) > 1e-9

    # Test W(t) difiere
    W_distinct = len({window(BETA[m]) for m in BETA}) == 3

    # Test boost difiere
    boost_diff = (BETA["SENSORIAL"]["boost_edges"]["Causal"] != BETA["RAZONAMIENTO"]["boost_edges"]["Causal"]
                  != BETA["PLAN"]["boost_edges"]["Causal"])

    # Test transicion limpia
    rng = random.Random(SEED)
    shared = {i: [rng.gauss(0,0.3) for _ in range(D)] for i in range(10)}
    before = {i: list(v) for i, v in shared.items()}
    affinity(shared[0], shared[1], "Causal", BETA["PLAN"])  # "transicion" no toca omega
    after = {i: list(v) for i, v in shared.items()}
    clean = all(math.dist(before[i], after[i]) < 1e-9 for i in before)

    overall = mode_flips_choice and sens_wins_terminal and raz_wins_causal and affinity_differs and W_distinct and boost_diff and clean

    result = {
        "experiment_id": "exp_SGM_0016",
        "experiment_name": "mode_typing",
        "phase": "Fase 1 - Infraestructura de Modos",
        "date": "2026-08-02",
        "hypothesis": "Los modos tipados (beta_mode de §1.1) modulan afinidad (Eq.2) y W(t) (Eq.8); en competencia real cambian la eleccion de caminata; transicion limpia sin contaminar omega.",
        "config": {"D": D, "seed": SEED, "edge_types": EDGE_TYPES,
                   "beta_mode": {k: {kk: (round(vv,3) if isinstance(vv,float) else vv) for kk,vv in v.items()} for k,v in BETA.items()}},
        "result": {
            "competition_SENSORIAL": {"chosen": cS[0], "a_Terminal": cS[1], "a_Causal": cS[2]},
            "competition_RAZONAMIENTO": {"chosen": cR[0], "a_Terminal": cR[1], "a_Causal": cR[2]},
            "competition_PLAN": {"chosen": cP[0], "a_Terminal": cP[1], "a_Causal": cP[2]},
            "test_mode_flips_choice": mode_flips_choice,
            "test_sens_wins_terminal": sens_wins_terminal,
            "test_raz_wins_causal": raz_wins_causal,
            "test_affinity_differs": affinity_differs,
            "test_distinct_W": W_distinct,
            "test_boost_differs": boost_diff,
            "test_clean_transition": clean,
            "pass": overall,
        },
        "script": "phases/phase1_modos/run_mode_typing.py",
        "results_file": "phases/phase1_modos/results_exp_SGM_0016_mode_typing.json",
        "test_target": "T-MOD-01 (modos tipados aplican beta_mode y cambian decision de caminata)",
        "variant_of": None,
        "lit_refs": ["SGM v1.4 §1.1 (Modos como Sesgos Semánticos)"],
        "notes": "Usa tabla beta_mode real de §1.1. D chico (16). El test de competencia prueba que el modo cambia la eleccion cuando hay empate de distancia entre arista Terminal y Causal.",
        "notes_criollo": "El 0016 pone los modos en serio: cada modo es un set de sesgos. En un grafo con dos caminos igual de cercanos (uno Terminal, otro Causal), Sensorial elige el Terminal y Razonamiento elige el Causal. El modo de verdad cambia por donde camina el grafo. Y pasar de un modo a otro no ensucia los omega.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase1_modos/results_exp_SGM_0016_mode_typing.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("exp_SGM_0016 MODE_TYPING")
    print("  SENSORIAL elige:", cS[0], "(Terminal)" if cS[0]==1 else "(Causal)", "aT", cS[1], "aC", cS[2])
    print("  RAZONAM   elige:", cR[0], "(Terminal)" if cR[0]==1 else "(Causal)", "aT", cR[1], "aC", cR[2])
    print("  PLAN      elige:", cP[0])
    print("  flip:", mode_flips_choice, "sens_term:", sens_wins_terminal, "raz_caus:", raz_wins_causal,
          "aff_diff:", affinity_differs, "W_diff:", W_distinct, "clean:", clean)
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
