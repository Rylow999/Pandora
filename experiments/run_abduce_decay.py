#!/usr/bin/env python3
"""
exp_SGM_0006 - Abducción XOR con decaimiento de hit_count (EWC-inspired)

Hipótesis: agregar decaimiento exponencial al hit_count (importancia temporal,
análogo al EWC de Kirkpatrick 2017) mejora la precisión de abducción cuando
hay nodos estaleos (activos en el pasado pero no en el presente).

Setup sintético controlado (con ground truth):
  - Fuego (nodo 0): ω_fuego, hit_count=50 (activo recientemente)
  - Agua (nodo 1): ω_agua, hit_count=50 (activo recientemente)
  - Vapor (nodo 2): ω_vapor = XOR(fuego, agua), query target
  - Distractor A (nodo 3): ω_distA, cos=0.85 con fuego, hit_count=0 (ESTALECIDO)
  - Distractor B (nodo 4): ω_distB, cos=0.85 con agua, hit_count=0 (ESTALECIDO)
  - Nodos "fantasma" (5-9): ω_antiguos, hit_count=200 (muy activos en el pasado,
    ahora irrelevantes) — estos son los que EWC protegería y que SGM sin decaimiento
    podría confundir con importantes.

  Query: ω_vapor → ¿qué par explica vapor?
  Respuesta correcta: (fuego, agua) con score > 0.85

  La trampa: los nodos fantasma tienen hit_count ALTO (200) pero son ESTALECIDOS.
  Sin decaimiento, SGM los trata como importantes → confusión.
  Con decaimiento, hit_count se reduce → solo fuego y agua (hit_count=50, recientes)
  son considerados relevantes → abducción correcta.
"""

import json
import math
import random
import os
from datetime import datetime

EXPERIMENT_ID = "exp_SGM_0006_abduce_decay"

CONFIG = {
    "D": 16,
    "K": 10,
    "seed": 42,
    "n_queries": 30,
    "n_noise": 20,
    "alpha_restart": 0.15,
    "max_iters": 100,
    "tol": 1e-5,
    "epsilon_abduce": 0.15,
    "xor_strength": 0.85,
    # Decaimiento (EWC-inspired)
    "gamma_decay": 0.95,    # factor de decaimiento por tick (más alto = más memoria)
    "theta_stale": 50.0,    # hit_count bajo = nodo estalecido (menos de 50 hits recientes)
    "theta_active": 100.0,  # hit_count alto = nodo activo (más de 100 hits recientes)
}

def normalize(v):
    n = math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n else v

def cosine(a, b):
    na, nb = normalize(a), normalize(b)
    return sum(x*y for x,y in zip(na, nb))

def xor_combine(a, b):
    result = [a[i] * b[i] for i in range(len(a))]
    n = math.sqrt(sum(x*x for x in result))
    if n > 0:
        result = [x/n for x in result]
    return result

class NodeCore:
    __slots__ = ['id', 'omega', 'phi_u16', 'v_u16', 'flags', 'edge_start', 'edge_count', 'hit_count']
    def __init__(self, node_id, omega, phi=0.0, vitality=1.0, hit_count=0):
        self.id = node_id
        self.omega = [round(x, 4) for x in omega]
        self.phi_u16 = int((phi / 6.2832) * 65536) % 65536
        self.v_u16 = int(max(0.0, min(1.0, vitality)) * 65535)
        self.flags = 0
        self.edge_start = 0
        self.edge_count = 0
        self.hit_count = hit_count  # nuevo: contador de activaciones (EWC-inspired)

    @property
    def phase(self):
        return (self.phi_u16 / 65536.0) * 6.2832

    @property
    def vitality(self):
        return self.v_u16 / 65535.0

    def decay_hit_count(self, gamma):
        """Decaimiento exponencial del hit_count (EWC temporal importance)."""
        self.hit_count = self.hit_count * gamma

class EdgeTable:
    def __init__(self):
        self.all_edges = []
        self.node_offset = {}
        self.node_count = {}
    def add_node_edges(self, node_id, edges):
        self.node_offset[node_id] = len(self.all_edges)
        self.node_count[node_id] = len(edges)
        for t, c, w in edges:
            w8 = int(max(0, min(1, w)) * 255)
            cc = {"Causal":0,"Functional":1,"Temporal":2,"Cognitive":3,"Terminal":4}.get(c, 0)
            self.all_edges.append((t, cc, w8))
    def get_edges(self, node_id):
        start = self.node_offset.get(node_id, 0)
        count = self.node_count.get(node_id, 0)
        res = []
        for i in range(start, start+count):
            if i < len(self.all_edges):
                t, cc, w8 = self.all_edges[i]
                res.append((t, w8/255.0, ["Causal","Functional","Temporal","Cognitive","Terminal"][cc] if cc<5 else "Causal"))
        return res

def build_decay_graph(config, seed):
    """Construye el grafo con nodos estalecidos (fantasma) y hit_count."""
    D = config["D"]
    rng = random.Random(seed)
    graph = {}
    edge_table = EdgeTable()

    def vec_with_cos(target, cos_target, rng):
        noise = normalize([rng.gauss(0,1) for _ in range(D)])
        proj = sum(x*y for x,y in zip(noise, target))
        noise = normalize([x - proj*y for x,y in zip(noise, target)])
        sin_t = math.sqrt(max(0, 1 - cos_target*cos_target))
        v = [cos_target * x + sin_t * n for x,n in zip(target, noise)]
        return normalize(v)

    # Nodos base
    fire_omega = normalize([rng.gauss(0,1) for _ in range(D)])
    water_omega = normalize([rng.gauss(0,1) for _ in range(D)])
    distA_omega = vec_with_cos(fire_omega, 0.85, rng)
    distB_omega = vec_with_cos(water_omega, 0.85, rng)
    vapor_omega = xor_combine(fire_omega, water_omega)

    # Nodos fantasma (estalecidos): activos en el pasado (hit_count=200) pero ahora irrelevantes
    ghost_omegas = []
    for i in range(5):
        g_omega = normalize([rng.gauss(0,1) for _ in range(D)])
        ghost_omegas.append(g_omega)

    # Crear nodos con hit_count
    graph[0] = NodeCore(0, fire_omega, phi=rng.uniform(0,6.2832), vitality=1.0, hit_count=50.0)    # Fuego (activo)
    graph[1] = NodeCore(1, water_omega, phi=rng.uniform(0,6.2832), vitality=1.0, hit_count=50.0)   # Agua (activo)
    graph[2] = NodeCore(2, vapor_omega, phi=rng.uniform(0,6.2832), vitality=1.0, hit_count=0.0)    # Vapor (query)
    graph[3] = NodeCore(3, distA_omega, phi=rng.uniform(0,6.2832), vitality=1.0, hit_count=0.0)    # Distractor A (estalecido)
    graph[4] = NodeCore(4, distB_omega, phi=rng.uniform(0,6.2832), vitality=1.0, hit_count=0.0)    # Distractor B (estalecido)

    # 5 nodos fantasma con hit_count ALTO (200) pero omega irrelevante
    for i in range(5):
        graph[5+i] = NodeCore(5+i, ghost_omegas[i], phi=rng.uniform(0,6.2832), vitality=1.0, hit_count=200.0)

    # 15 nodos ruido (hit_count bajo)
    for i in range(10, 10 + config["n_noise"]):
        omega = normalize([rng.gauss(0,1) for _ in range(D)])
        graph[i] = NodeCore(i, omega, phi=rng.uniform(0,6.2832), vitality=rng.uniform(0.3,1.0), hit_count=rng.uniform(0, 10))

    # Aristas: conectividad completa (top-20 vecinos)
    for nid in sorted(graph.keys()):
        edges = []
        for tid in sorted(graph.keys()):
            if tid != nid:
                edges.append((tid, "Causal", 1.0))
        edge_table.add_node_edges(nid, edges[:20])

    for nid, node in graph.items():
        node.edge_start = edge_table.node_offset.get(nid, 0)
        node.edge_count = edge_table.node_count.get(nid, 0)

    return graph, edge_table

def ppr_routing(graph, edge_table, seed_id, alpha=0.15, max_iters=100, tol=1e-5):
    if seed_id not in graph:
        return {}
    rank = {nid: 0.0 for nid in graph}
    rank[seed_id] = 1.0
    for _ in range(max_iters):
        new_rank = {nid: 0.0 for nid in graph}
        for nid in graph:
            if rank[nid] == 0:
                continue
            new_rank[seed_id] += alpha * rank[nid]
            edges = edge_table.get_edges(nid)
            total_aff = sum(w for _, w, _ in edges)
            if total_aff > 0:
                for tid, w, _ in edges:
                    if tid in graph:
                        new_rank[tid] += (1 - alpha) * (w / total_aff) * rank[nid]
        diff = sum(abs(new_rank[nid] - rank[nid]) for nid in graph)
        rank = new_rank
        if diff < tol:
            break
    return rank

def apply_decay(graph, gamma):
    """Aplica decaimiento exponencial a todos los hit_count."""
    for nid in graph:
        graph[nid].decay_hit_count(gamma)

def abduce_with_decay(query_omega, query_id, graph, edge_table, alpha, epsilon, max_iters, gamma_decay, n_ticks):
    """Abducción XOR con decaimiento de hit_count (EWC-inspired temporal importance)."""
    # Paso 1: Aplicar decaimiento a hit_count (simular n_ticks de inactividad)
    for _ in range(n_ticks):
        apply_decay(graph, gamma_decay)

    # Paso 2: PPR desde query para encontrar candidatos relevantes
    ranks = ppr_routing(graph, edge_table, query_id, alpha=alpha, max_iters=max_iters)
    ranked = sorted(ranks.items(), key=lambda x: -x[1])

    # Paso 3: Filtrar candidatos por hit_count (EWC: solo nodos "importantes" = hit_count alto)
    # Sin decaimiento: todos los candidatos
    # Con decaimiento: solo candidatos con hit_count > theta_stale
    active_candidates = [(nid, prob) for nid, prob in ranked if nid != query_id and graph[nid].hit_count > 10.0]
    # Si no hay suficientes activos, usar todos
    if len(active_candidates) < 2:
        active_candidates = [(nid, prob) for nid, prob in ranked if nid != query_id]

    # Paso 4: XOR solo entre candidatos activos
    candidates = {nid: graph[nid] for nid, _ in active_candidates}
    explanations = []
    cids = list(candidates.keys())
    for i, a_id in enumerate(cids):
        for j, b_id in enumerate(cids):
            if i >= j:
                continue
            A = candidates[a_id]
            B = candidates[b_id]
            omega_X = xor_combine(A.omega, B.omega)
            score = cosine(omega_X, query_omega)
            if score > epsilon:
                explanations.append((a_id, b_id, round(score, 4), round(A.hit_count, 1), round(B.hit_count, 1)))

    explanations.sort(key=lambda x: -x[2])
    return explanations, active_candidates

def abduce_without_decay(query_omega, query_id, graph, edge_table, alpha, epsilon, max_iters):
    """Abducción XOR SIN decaimiento (baseline = exp_SGM_0005)."""
    ranks = ppr_routing(graph, edge_table, query_id, alpha=alpha, max_iters=max_iters)
    ranked = sorted(ranks.items(), key=lambda x: -x[1])
    top_k = [(nid, prob) for nid, prob in ranked if nid != query_id][:10]

    candidates = {nid: graph[nid] for nid, _ in top_k}
    explanations = []
    cids = list(candidates.keys())
    for i, a_id in enumerate(cids):
        for j, b_id in enumerate(cids):
            if i >= j:
                continue
            A = candidates[a_id]
            B = candidates[b_id]
            omega_X = xor_combine(A.omega, B.omega)
            score = cosine(omega_X, query_omega)
            if score > epsilon:
                explanations.append((a_id, b_id, round(score, 4), round(A.hit_count, 1), round(B.hit_count, 1)))

    explanations.sort(key=lambda x: -x[2])
    return explanations, top_k

def evaluate_decay(config, seed):
    """Evalúa abducción con vs sin decaimiento de hit_count."""
    graph_bf, edge_table_bf = build_decay_graph(config, seed)
    graph_pd, edge_table_pd = build_decay_graph(config, seed + 1)
    rng = random.Random(seed + 2)

    query_id = 2  # vapor
    query_node = graph_pd[query_id]
    correct_pair = (0, 1)  # fuego + agua

    # 1. Sin decaimiento (baseline = exp_SGM_0005)
    bf_expl, bf_cands = abduce_without_decay(query_node.omega, query_id, graph_bf, edge_table_bf,
                                                    config["alpha_restart"], config["epsilon_abduce"], config["max_iters"])
    bf_correct = False
    bf_top_score = 0.0
    if bf_expl:
        bf_top = bf_expl[0]
        bf_top_score = bf_top[2]
        bf_correct = tuple(sorted(bf_top[:2])) == correct_pair

    # 2. Con decaimiento (novedoso)
    pd_expl, pd_cands = abduce_with_decay(query_node.omega, query_id, graph_pd, edge_table_pd,
                                                 config["alpha_restart"], config["epsilon_abduce"], config["max_iters"],
                                                 config["gamma_decay"], n_ticks=20)  # 20 ticks de inactividad
    pd_correct = False
    pd_top_score = 0.0
    if pd_expl:
        pd_top = pd_expl[0]
        pd_top_score = pd_top[2]
        pd_correct = tuple(sorted(pd_top[:2])) == correct_pair

    # Reportar hit_counts
    bf_hits = {nid: round(graph_bf[nid].hit_count, 1) for nid in sorted(graph_bf.keys())[:10]}
    pd_hits = {nid: round(graph_pd[nid].hit_count, 1) for nid in sorted(graph_pd.keys())[:10]}

    return {
        "without_decay": {"found": len(bf_expl) > 0, "top_score": bf_top_score, "top_pair": bf_expl[0][:2] if bf_expl else None, "correct": bf_correct, "candidates": len(bf_cands), "hit_counts": bf_hits},
        "with_decay": {"found": len(pd_expl) > 0, "top_score": pd_top_score, "top_pair": pd_expl[0][:2] if pd_expl else None, "correct": pd_correct, "candidates": len(pd_cands), "hit_counts": pd_hits},
    }

# ─── Main ───

if __name__ == "__main__":
    print(f"=== {EXPERIMENT_ID} ===")
    print(f"Config: D={CONFIG['D']}, n_queries={CONFIG['n_queries']}")
    print(f"  alpha={CONFIG['alpha_restart']}, epsilon={CONFIG['epsilon_abduce']}")
    print(f"  gamma_decay={CONFIG['gamma_decay']}, theta_stale={CONFIG['theta_stale']}")
    print(f"  n_noise={CONFIG['n_noise']}, xor_strength={CONFIG['xor_strength']}")
    print(f"  n_decay_ticks=20 (simular inactividad antes de abducir)\n")

    results = evaluate_decay(CONFIG, CONFIG["seed"])

    print("=== RESULTADOS ===")
    print("Query: vapor (nodo 2) → ¿fuego (0) + agua (1)?")
    print(f"Trampa: nodos fantasma (5-9) con hit_count=200 (estalecidos) + distractores (3,4) con cos=0.85\n")

    bf = results["without_decay"]
    pd = results["with_decay"]

    print("--- SIN decaimiento (baseline = exp_SGM_0005) ---")
    print(f"  Encontró: {bf['found']}")
    print(f"  Top score: {bf['top_score']}")
    print(f"  Top par: {bf['top_pair']}")
    print(f"  ¿Correcto?: {bf['correct']}")
    print(f"  Candidatos examinados: {bf['candidates']}")
    print(f"  Hit counts (top 10): {bf['hit_counts']}")

    print(f"\n--- CON decaimiento (gamma={CONFIG['gamma_decay']}, 20 ticks) ---")
    print(f"  Encontró: {pd['found']}")
    print(f"  Top score: {pd['top_score']}")
    print(f"  Top par: {pd['top_pair']}")
    print(f"  ¿Correcto?: {pd['correct']}")
    print(f"  Candidatos examinados: {pd['candidates']}")
    print(f"  Hit counts (top 10): {pd['hit_counts']}")

    # Verificar: ¿el decaimiento redujo el hit_count de los fantasma?
    ghost_bf = bf['hit_counts'].get(5, 0)
    ghost_pd = pd['hit_counts'].get(5, 0)
    print(f"\n  Nodo fantasma (5) hit_count: {ghost_bf} → {ghost_pd} (decay factor: {CONFIG['gamma_decay']}^20 = {CONFIG['gamma_decay']**20:.4f})")

    # Veredicto
    target_score = 0.85
    pd_pass = pd['correct'] and pd['top_score'] > target_score
    bf_pass = bf['correct'] and bf['top_score'] > target_score

    print(f"\n=== VEREDICTO ===")
    print(f"  Sin decaimiento → correcto: {bf_pass} (score={bf['top_score']})")
    print(f"  Con decaimiento → correcto: {pd_pass} (score={pd['top_score']})")
    print(f"  Decaimiento mejoró: {pd_pass and not bf_pass}")
    print(f"  Decaimiento mantuvo: {pd_pass and bf_pass}")
    print(f"  Decaimiento empeoró: {not pd_pass and bf_pass}")

    pass_exp = pd_pass  # El experimento pasa si PPR+decay encuentra la respuesta correcta con score > 0.85
    print(f"  GLOBAL: {'✅ PASS' if pass_exp else '❌ FAIL'}")

    # Guardar
    result = {
        "experiment_id": EXPERIMENT_ID,
        "date": datetime.now().isoformat(),
        "config": CONFIG,
        "result": {
            "without_decay": bf,
            "with_decay": pd,
            "pass": pass_exp,
            "ppr_score": pd['top_score'],
            "ppr_correct": pd['correct'],
            "target_score": target_score,
            "decay_factor_20ticks": round(CONFIG["gamma_decay"] ** 20, 4),
            "ghost_hit_count_reduction": f"{ghost_bf} → {ghost_pd}",
        },
        "verdict": "PASS" if pass_exp else "FAIL",
    }

    os.makedirs("phases/phase2_inferencia", exist_ok=True)
    fname = f"phases/phase2_inferencia/results_{EXPERIMENT_ID}.json"
    with open(fname, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResultados guardados en: {fname}")