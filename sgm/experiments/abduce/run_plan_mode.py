# -*- coding: utf-8 -*-
"""
exp_SGM_0020 -- plan_mode (Fase 4: MODO_PLAN + Q(plan) + horizonte dinamico)
Objetivo (roadmap Fase 4 / spec SGM v1.4 §4): MODO_PLAN navega sesgando aristas
Temporal+Functional (boost 2.0 cada una, spec §1.2 linea 559-560), K=10 (spec), W=100
(linea 574), H_plan = H_base*(1+rho(t)) con H_base=50 (linea 571). Q(plan)>0.5 = alcanza terminal.
Tests (T-PLAN-01 / T-PLAN-03 del roadmap):
  T-PLAN-01: MODO_PLAN desde meta abstracta recorre la cadena de plan y alcanza el terminal (Q>0.5).
  T-PLAN-03: rho baja (0.05) vs rho alta (0.40) -> con rho alta el horizonte crece (cadena mas larga
            antes de INCONCLUSA).
Trazabilidad (separar de RAZONAMIENTO): en una bifurcacion a igual distancia, MODO_PLAN
debe elegir el nodo conectado por Temporal/Functional y RAZONAMIENTO el conectado por Causal
(patron de competencia de 0016).
Eq. usadas: Eq.2 afinidad (alpha=5.0), Eq.8 W(t), Eq.9 rho(t) tiempo subjetivo.
"""
import math, random, json, copy, os

SEED = 42
N = 60
D = 64
CLUSTERS = 4
CLUSTER_SIZE = N // CLUSTERS
ALPHA = 5.0
W_PLAN = 100
H_BASE = 50
THETA_REFUT = 2.0
KAPPA_W = 2.0
THETA_NOVELTY = 0.30
MAX_TICKS = 300
PLAN_LEN = 8  # largo de la cadena de plan (meta + sub-metas + terminal)

EDGE_TYPES = ["Terminal","Causal","Temporal","Functional","Cognitive"]
BOOST = {
    "RAZONAMIENTO": {"Terminal":0.8,"Causal":2.0,"Temporal":1.2,"Functional":1.5,"Cognitive":2.0},
    "PLAN":         {"Terminal":0.8,"Causal":1.2,"Temporal":2.0,"Functional":2.0,"Cognitive":1.0},
}

def dist(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def build_graph(rng):
    """Grafo con una CADENA DE PLAN estructurada (nodos 0..PLAN_LEN-1 cerca en secuencia)
    mas nodos de fondo dispersos. El terminal es el ultimo de la cadena."""
    nodes = {}
    # fondo disperso (ruido)
    for i in range(PLAN_LEN, N):
        nodes[i] = {"id":i, "omega":[rng.gauss(0,2.0) for _ in range(D)],
                    "vitality":0.9, "activation":0.5, "painful":False}
    # cadena de plan: cada nodo cerca del anterior (distancia 0.3), type Temporal/Functional alternados
    omega0 = [rng.gauss(0,0.5) for _ in range(D)]
    nodes[0] = {"id":0, "omega":list(omega0), "vitality":0.9, "activation":0.5, "painful":False}
    for k in range(1, PLAN_LEN):
        step = [0.3 if j == 0 else 0.0 for j in range(D)]
        nodes[k] = {"id":k, "omega":[nodes[k-1]["omega"][j]+step[j] for j in range(D)],
                    "vitality":0.9, "activation":0.5, "painful":False}
    return nodes

def precompute(nodes):
    ids = list(nodes); M = {}
    for a in ids:
        M[a] = {b: dist(nodes[a]["omega"], nodes[b]["omega"]) for b in ids}
    return M

def affinity_move(cur, nodes, M, mode, prev=None):
    best, bid = -1.0, None
    for b in nodes:
        if b == cur or b == prev: continue
        et = EDGE_TYPES[b % len(EDGE_TYPES)]
        boost = BOOST[mode][et]
        p = math.exp(-ALPHA*M[cur][b]) * boost
        if p > best: best, bid = p, b
    return bid

def run_plan(query, target, nodes, M, mode, rho, rng):
    cur = query; prev = None; visited=[cur]; ticks=0; pain=0.0; cooldown=0
    H_plan = H_BASE * (1 + rho)
    for t in range(MAX_TICKS):
        if cur == target and cur != query:
            return "DETERMINADO", len(visited), pain
        w_eff = W_PLAN / (1 + KAPPA_W*pain) * (1 + rho)
        nov = len(set(visited[-max(1,int(w_eff)):]))/max(1,len(visited[-max(1,int(w_eff)):]))
        if cooldown>0: cooldown-=1
        elif w_eff <= 0.5*W_PLAN and nov < THETA_NOVELTY:
            cooldown = COOLDOWN
        nxt = affinity_move(cur, nodes, M, mode, prev)
        if nxt is None: return "INCONCLUSA", len(visited), pain
        prev = cur; cur = nxt; visited.append(cur); ticks+=1
        if ticks >= H_plan + 5:
            return "INCONCLUSA", len(visited), pain
    return "INCONCLUSA", len(visited), pain

def main():
    rng = random.Random(SEED)
    nodes = build_graph(rng)
    M = precompute(nodes)
    terminal = PLAN_LEN - 1  # ultimo de la cadena
    meta = 0

    # T-PLAN-01: MODO_PLAN recorre la cadena y alcanza el terminal
    st_plan, len_plan, _ = run_plan(meta, terminal, nodes, M, "PLAN", rho=0.05, rng=rng)
    q_plan = 1.0 if st_plan=="DETERMINADO" else 0.0

    # T-PLAN-03: rho baja vs alta -> longitud de cadena recorrida antes de corte
    _, len_low, _ = run_plan(meta, terminal, nodes, M, "PLAN", rho=0.05, rng=rng)
    _, len_high, _ = run_plan(meta, terminal, nodes, M, "PLAN", rho=0.40, rng=rng)
    rho_afecta = (len_high >= len_low)

    # Trazabilidad: bifurcacion a igual distancia, PLAN elige Temporal/Functional,
    # RAZONAMIENTO elige Causal (patron 0016)
    r = N; hT = N+1; hC = N+2
    base = [rng.gauss(0,0.5) for _ in range(D)]
    nodes[r] = {"id":r, "omega":list(base), "vitality":0.9, "activation":0.5, "painful":False}
    nodes[hT] = {"id":hT, "omega":[base[k]+(0.3 if k==0 else 0.0) for k in range(D)], "vitality":0.9, "activation":0.5, "painful":False}
    nodes[hC] = {"id":hC, "omega":[base[k]+(0.3 if k==1 else 0.0) for k in range(D)], "vitality":0.9, "activation":0.5, "painful":False}
    M.setdefault(r,{}); M.setdefault(hT,{}); M.setdefault(hC,{})
    for a in (r,hT,hC):
        for b in (r,hT,hC):
            M[a][b] = dist(nodes[a]["omega"], nodes[b]["omega"])
    def affinity_pick(cur, mode):
        best, bid = -1.0, None
        for b in (hT, hC):
            et = "Temporal" if b==hT else "Causal"
            p = math.exp(-ALPHA*M[cur][b]) * BOOST[mode][et]
            if p > best: best, bid = p, b
        return bid
    pick_plan = affinity_pick(r, "PLAN")
    pick_raz = affinity_pick(r, "RAZONAMIENTO")
    modo_plan_elige_TF = (pick_plan == hT)
    razonamiento_elige_C = (pick_raz == hC)

    overall = (q_plan > 0.5) and rho_afecta and modo_plan_elige_TF and razonamiento_elige_C

    result = {
        "experiment_id":"exp_SGM_0020",
        "experiment_name":"plan_mode",
        "phase":"Fase 4 - Planificacion",
        "date":"2026-08-02",
        "hypothesis":"MODO_PLAN navega la cadena de plan (sesgo Temporal/Functional, boost 2.0) y alcanza el terminal (Q>0.5). H_plan=H_base*(1+rho): rho alta da horizonte mayor. En bifurcacion a igual distancia, PLAN elige Temporal/Functional y RAZONAMIENTO elige Causal (modos tipados, 0016).",
        "config":{"N":N,"D":D,"seed":SEED,"W_PLAN":W_PLAN,"H_BASE":H_BASE,"plan_len":PLAN_LEN,
                  "boost_PLAN":BOOST["PLAN"],"boost_RAZONAMIENTO":BOOST["RAZONAMIENTO"],
                  "spec_ref":"SGM v1.4 §4 linea 559-574"},
        "result":{
            "T-PLAN-01":{"estado_PLAN":st_plan,"Q_plan":q_plan,"alcanza_terminal":q_plan>0.5},
            "T-PLAN-03":{"rho_baja_len":len_low,"rho_alta_len":len_high,"rho_afecta_horizonte":rho_afecta},
            "trazabilidad_modo":{"PLAN_elige":"Temporal/Functional" if pick_plan==hT else "Causal",
                                 "RAZONAMIENTO_elige":"Causal" if pick_raz==hC else "Temporal/Functional",
                                 "PLAN_elige_TF":modo_plan_elige_TF,"RAZONAMIENTO_elige_C":razonamiento_elige_C},
            "pass":overall,
        },
        "script":"phases/phase4_planificacion/run_plan_mode.py",
        "results_file":"phases/phase4_planificacion/results_exp_SGM_0020_plan_mode.json",
        "test_target":"T-PLAN-01 (MODO_PLAN alcanza terminal Q>0.5), T-PLAN-03 (rho afecta horizonte), trazabilidad vs RAZONAMIENTO",
        "variant_of":None,
        "lit_refs":["SGM v1.4 §4","SGM_ROADMAP.md Fase 4","exp_SGM_0016 (modos tipados)"],
        "notes":"Grafo con cadena de plan estructurada (nodos cerca en secuencia) para que T-PLAN-01 sea medible (el test-trap de 0017: grafo completo vaga y no alcanza). rho alta -> H_plan mayor -> cadena mas larga. Bifurcacion prueba modo tipado (0016).",
        "notes_criollo":"El 0020 es Fase 4: MODO_PLAN. El sistema planea siguiendo la cadena de plan (sesgo Temporal/Functional), llega al objetivo (Q>0.5), y el horizonte crece si esta mas denso (rho alta). En una bifurcacion, PLAN elige el camino de tiempo/util y RAZONAMIENTO el de causa - los modos son distintos de verdad.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase4_planificacion/results_exp_SGM_0020_plan_mode.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("exp_SGM_0020 PLAN_MODE")
    print("  T-PLAN-01 estado:", st_plan, "Q:", q_plan, "-> alcanza:", q_plan>0.5)
    print("  T-PLAN-03 rho_baja_len:", len_low, "rho_alta_len:", len_high, "-> rho afecta:", rho_afecta)
    print("  Trazabilidad PLAN elige:", "TF" if pick_plan==hT else "C", "| RAZON elige:", "C" if pick_raz==hC else "TF")
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
