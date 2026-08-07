#!/usr/bin/env python3
"""
exp_SGM_0005 - Abducción XOR guiada por PPR

Hipótesis: PPR guía la búsqueda de pares para abducción XOR, encontrando
explicaciones multi-hop con score > 0.85, superando brute-force O(n²)
cuando la respuesta está a 2+ hops.

Setup sintético controlado (con ground truth):
  - Fuego (nodo 1): ω_fuego
  - Agua (nodo 2): ω_agua
  - Vapor (nodo 3): ω_vapor = XOR(fuego, agua)  [ground truth]
  - Distractor A (nodo 4): ω_distA, cercano a fuego solo
  - Distractor B (nodo 5): ω_distB, cercano a agua solo
  - 20 nodos ruido

  Query: ω_vapor → ¿qué par explica vapor?
  Respuesta correcta: (fuego, agua) con score > 0.85

  La trampa: distractor A tiene más afinidad directa con vapor que agua,
  pero (fuego, agua) es la única combinación XOR que produce vapor.
"""

import json
import math
import random
import os
from datetime import datetime

EXPERIMENT_ID = "exp_SGM_0005_abduce_ppr"

CONFIG = {
    "D": 16,
    "K": 10,
    "seed": 42,
    "n_queries": 30,
    "n_noise": 20,
    "alpha_restart": 0.15,
    "max_iters": 100,
    "tol": 1e-5,
    "epsilon_abduce": 0.15,   # threshold de coseno para abducción
    "xor_strength": 0.85,     # qué tan fuerte es la señal XOR
}

def normalize(v):
    n = math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n else v

def cosine(a, b):
    na, nb = normalize(a), normalize(b)
    return sum(x*y for x,y in zip(na, nb))

def xor_combine(a, b):
    """Generative XOR: element-wise product + sum (simplificado para D=16)."""
    # Producto element-wise (binding) + suma (aggregation)
    # Esto es análogo al binding de HDC / spatter coding
    result = [a[i] * b[i] for i in range(len(a))]
    # Normalizar para que sea un vector unitario
    n = math.sqrt(sum(x*x for x in result))
    if n > 0:
        result = [x/n for x in result]
    return result

class NodeCore:
    __slots__ = ['id', 'omega', 'phi_u16', 'v_u16', 'flags', 'edge_start', 'edge_count']
    def __init__(self, node_id, omega, phi=0.0, vitality=1.0):
        self.id = node_id
        self.omega = [round(x, 4) for x in omega]
        self.phi_u16 = int((phi / 6.2832) * 65536) % 65536
        self.v_u16 = int(max(0.0, min(1.0, vitality)) * 65535)
        self.flags = 0
        self.edge_start = 0
        self.edge_count = 0

    @property
    def phase(self):
        return (self.phi_u16 / 65536.0) * 6.2832

    @property
    def vitality(self):
        return self.v_u16 / 65535.0

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

def build_abduce_graph(config, seed):
    """Construye el grafo para abducción XOR con trampa de distractores."""
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

    # Distractor A: cercano a fuego (cos=0.85)
    distA_omega = vec_with_cos(fire_omega, 0.85, rng)
    # Distractor B: cercano a agua (cos=0.85)
    distB_omega = vec_with_cos(water_omega, 0.85, rng)

    # Vapor = XOR(fuego, agua) — ground truth
    vapor_omega = xor_combine(fire_omega, water_omega)

    graph[0] = NodeCore(0, fire_omega, phi=rng.uniform(0,6.2832), vitality=1.0)    # Fuego
    graph[1] = NodeCore(1, water_omega, phi=rng.uniform(0,6.2832), vitality=1.0)    # Agua
    graph[2] = NodeCore(2, vapor_omega, phi=rng.uniform(0,6.2832), vitality=1.0)    # Vapor (query target)
    graph[3] = NodeCore(3, distA_omega, phi=rng.uniform(0,6.2832), vitality=1.0)    # Distractor A (cerca de fuego)
    graph[4] = NodeCore(4, distB_omega, phi=rng.uniform(0,6.2832), vitality=1.0)    # Distractor B (cerca de agua)

    # 20 nodos ruido
    for i in range(5, 5 + config["n_noise"]):
        omega = normalize([rng.gauss(0,1) for _ in range(D)])
        graph[i] = NodeCore(i, omega, phi=rng.uniform(0,6.2832), vitality=rng.uniform(0.3,1.0))

    # Aristas: conectividad completa para abducción (todos los nodos conectados entre sí)
    # Esto simula un grafo denso donde PPR debe encontrar la combinación correcta
    for nid in sorted(graph.keys()):
        edges = []
        for tid in sorted(graph.keys()):
            if tid != nid:
                edges.append((tid, "Causal", 1.0))
        edge_table.add_node_edges(nid, edges[:20])  # top-20 vecinos por conexión

    for nid, node in graph.items():
        node.edge_start = edge_table.node_offset.get(nid, 0)
        node.edge_count = edge_table.node_count.get(nid, 0)

    return graph, edge_table, {0: "fuego", 1: "agua", 2: "vapor", 3: "distractor_A", 4: "distractor_B"}

def ppr_routing(graph, edge_table, seed_id, alpha=0.15, max_iters=100, tol=1e-5):
    """PPR sobre el grafo: random walk con restart en la semilla."""
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

def brute_force_abduce(query_omega, candidates, epsilon):
    """Abducción XOR brute-force O(n²): prueba todos los pares."""
    explanations = []
    for i, A in enumerate(candidates):
        for j, B in enumerate(candidates):
            if i >= j:
                continue
            omega_X = xor_combine(A.omega, B.omega)
            score = cosine(omega_X, query_omega)
            if score > epsilon:
                explanations.append((A.id, B.id, round(score, 4)))
    explanations.sort(key=lambda x: -x[2])
    return explanations

def ppr_guided_abduce(query_omega, query_id, graph, edge_table, alpha, epsilon, max_iters):
    """Abducción XOR guiada por PPR: PPR encuentra candidatos relevantes, luego XOR."""
    # Paso 1: PPR desde query para encontrar candidatos relevantes
    ranks = ppr_routing(graph, edge_table, query_id, alpha=alpha, max_iters=max_iters)
    ranked = sorted(ranks.items(), key=lambda x: -x[1])

    # Top-K candidatos (excluyendo el query)
    top_k = [(nid, prob) for nid, prob in ranked if nid != query_id][:10]

    # Paso 2: XOR solo entre candidatos top-K (O(K²) en vez de O(n²))
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
                explanations.append((a_id, b_id, round(score, 4)))

    explanations.sort(key=lambda x: -x[2])
    return explanations, top_k

def evaluate_abduce(config, seed):
    """Evalúa abducción brute-force vs PPR-guided."""
    graph, edge_table, names = build_abduce_graph(config, seed)
    rng = random.Random(seed + 1)

    query_id = 2  # vapor
    query_node = graph[query_id]
    correct_pair = (0, 1)  # fuego + agua

    results = {
        "brute_force": {"found": False, "top_score": 0.0, "top_pair": None, "time_complexity": "O(n²)"},
        "ppr_guided": {"found": False, "top_score": 0.0, "top_pair": None, "candidates_examined": 0, "time_complexity": "O(K²) donde K<<n"},
    }

    # 1. Brute-force
    bf = brute_force_abduce(query_node.omega, list(graph.values()), config["epsilon_abduce"])
    if bf:
        results["brute_force"]["found"] = True
        results["brute_force"]["top_score"] = bf[0][2]
        results["brute_force"]["top_pair"] = bf[0][:2]

    # 2. PPR-guided
    pg, top_k = ppr_guided_abduce(query_node.omega, query_id, graph, edge_table,
                                   config["alpha_restart"], config["epsilon_abduce"], config["max_iters"])
    results["ppr_guided"]["candidates_examined"] = len(top_k)
    if pg:
        results["ppr_guided"]["found"] = True
        results["ppr_guided"]["top_score"] = pg[0][2]
        results["ppr_guided"]["top_pair"] = pg[0][:2]

    # Verificar si encontró la respuesta correcta
    bf_correct = tuple(sorted(results["brute_force"]["top_pair"] or [])) == correct_pair
    pg_correct = tuple(sorted(results["ppr_guided"]["top_pair"] or [])) == correct_pair

    results["brute_force"]["correct"] = bf_correct
    results["ppr_guided"]["correct"] = pg_correct

    return results, names

# ─── Main ───

if __name__ == "__main__":
    print(f"=== {EXPERIMENT_ID} ===")
    print(f"Config: D={CONFIG['D']}, queries={CONFIG['n_queries']}")
    print(f"  alpha={CONFIG['alpha_restart']}, epsilon={CONFIG['epsilon_abduce']}")
    print(f"  xor_strength={CONFIG['xor_strength']}, n_noise={CONFIG['n_noise']}\n")

    results, names = evaluate_abduce(CONFIG, CONFIG["seed"])

    print("=== RESULTADOS ===")
    print(f"Query: vapor (nodo 2)")
    print(f"Respuesta correcta: fuego (0) + agua (1)")
    print(f"Distractores: distractor_A (3, cerca de fuego), distractor_B (4, cerca de agua)")
    print()

    bf = results["brute_force"]
    pg = results["ppr_guided"]

    print("--- Brute-Force O(n²) ---")
    print(f"  Encontró: {bf['found']}")
    print(f"  Top score: {bf['top_score']}")
    print(f"  Top par: {bf['top_pair']} → {[names.get(n, str(n)) for n in (bf['top_pair'] or [])]}")
    print(f"  ¿Correcto?: {bf['correct']}")
    print(f"  Complejidad: {bf['time_complexity']}")

    print(f"\n--- PPR-Guided O(K²), K={pg['candidates_examined']} ---")
    print(f"  Encontró: {pg['found']}")
    print(f"  Top score: {pg['top_score']}")
    print(f"  Top par: {pg['top_pair']} → {[names.get(n, str(n)) for n in (pg['top_pair'] or [])]}")
    print(f"  ¿Correcto?: {pg['correct']}")
    print(f"  Candidatos examinados: {pg['candidates_examined']}")
    print(f"  Complejidad: {pg['time_complexity']}")

    # Veredicto
    pg_acc = 1.0 if pg['correct'] else 0.0
    bf_acc = 1.0 if bf['correct'] else 0.0
    target_score = 0.85

    print(f"\n=== VEREDICTO ===")
    print(f"  PPR-guided encontró respuesta correcta: {pg['correct']}")
    print(f"  Score PPR-guided: {pg['top_score']} (objetivo: > {target_score})")
    print(f"  PPR-guided score > {target_score}: {pg['top_score'] > target_score}")
    print(f"  PPR-guided correcto Y score > target: {pg['correct'] and pg['top_score'] > target_score}")

    pass_exp = pg['correct'] and pg['top_score'] > target_score
    print(f"  GLOBAL: {'✅ PASS' if pass_exp else '❌ FAIL'}")

    # Guardar
    result = {
        "experiment_id": EXPERIMENT_ID,
        "date": datetime.now().isoformat(),
        "config": CONFIG,
        "result": {
            "brute_force": bf,
            "ppr_guided": pg,
            "pass": pass_exp,
            "ppr_score": pg['top_score'],
            "ppr_correct": pg['correct'],
            "target_score": target_score,
        },
        "verdict": "PASS" if pass_exp else "FAIL",
    }

    os.makedirs("phases/phase2_inferencia", exist_ok=True)
    fname = f"phases/phase2_inferencia/results_{EXPERIMENT_ID}.json"
    with open(fname, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResultados guardados en: {fname}")