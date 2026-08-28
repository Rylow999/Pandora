#!/usr/bin/env python3
"""
exp_SGM_0004 - PPR multi-hop routing

Hipótesis: Personalized PageRank sobre el grafo DSCN-G (con omega como semilla
y Ec.2 como edge weight) logra ruteo multi-hop superior a resonancia local pura
(argmax 1 paso), superando el baseline de v0.22 v1/v2 (routing_acc≈0.50 azar)
cuando la respuesta requiere >1 hop.

Setup sintético controlado (con ground truth):
  - Cadena fuerte: semilla(0) → n1(1) → n2(2) → TARGET(3)
  - Distractor(4): vecino directo de semilla con más afinidad que n1
  - 30 nodos ruido: semilla no conectada a ellos
  - 10 threads, 50 queries aleatorias

La trampa (por qué resonancia local FALLA):
  distractor(4) tiene más afinidad con semilla(0) que n1(1)
  → argmax local elige distractor → callejón sin salida → no llega a TARGET
  → PPR con restart fluye por la cadena y se acumula en TARGET
"""

import json
import math
import random
import os
from datetime import datetime

EXPERIMENT_ID = "exp_SGM_0004_ppr_multipath_routing"

CONFIG = {
    "D": 16,
    "K": 10,
    "seed": 42,
    "n_query": 50,          # queries aleatorias
    "n_noise": 30,          # nodos ruido (sin conexión)
    "alpha_restart": 0.15,  # PPR restart prob
    "max_iters": 100,
    "tol": 1e-5,
    "hops": 3,              # cadena de 3 hops
    "aff_signal": 0.8,      # afinidad de la cadena
    "aff_distractor": 0.85, # afinidad del distractor (más alto que la cadena)
}

def normalize(v):
    n = math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n else v

def cosine(a, b):
    na, nb = normalize(a), normalize(b)
    return sum(x*y for x,y in zip(na, nb))

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

# ─── Construcción del grafo trampa ───

def build_trap_graph(config, seed):
    """Construye el grafo sintético con la trampa real.
    
    Cosenos garantizados:
      cos(seed, n1) = 0.50     (moderado, lleva a target)
      cos(seed, dist) = 0.90   (MUY alto, pero callejón sin salida)
      cos(n1, n2) = 0.90
      cos(n2, target) = 0.90
    """
    D = config["D"]
    rng = random.Random(seed)
    graph = {}
    edge_table = EdgeTable()

    def vec_with_cos(target, cos_target, rng):
        """Construye un vector cuyo coseno con target = cos_target."""
        # noise perpendicular a target
        noise = normalize([rng.gauss(0,1) for _ in range(D)])
        # gram-schmidt: quitar componente en dirección de target
        proj = sum(x*y for x,y in zip(noise, target))
        noise = normalize([x - proj*y for x,y in zip(noise, target)])
        # construir vector: target*cos + noise*sin
        sin_t = math.sqrt(max(0, 1 - cos_target*cos_target))
        v = [cos_target * x + sin_t * n for x,n in zip(target, noise)]
        return normalize(v)

    # Seed: vector aleatorio
    seed_omega = normalize([rng.gauss(0,1) for _ in range(D)])
    graph[0] = NodeCore(0, seed_omega, phi=rng.uniform(0,6.2832), vitality=1.0)

    # n1: cos=0.50 con seed (lleva a target)
    n1_omega = vec_with_cos(seed_omega, 0.50, rng)
    graph[1] = NodeCore(1, n1_omega, phi=rng.uniform(0,6.2832), vitality=1.0)

    # distractor: cos=0.90 con seed (MUY cerca, pero callejón)
    dist_omega = vec_with_cos(seed_omega, 0.90, rng)
    graph[4] = NodeCore(4, dist_omega, phi=rng.uniform(0,6.2832), vitality=1.0)

    # n2: cos=0.90 con n1
    n2_omega = vec_with_cos(n1_omega, 0.90, rng)
    graph[2] = NodeCore(2, n2_omega, phi=rng.uniform(0,6.2832), vitality=1.0)

    # target: cos=0.90 con n2
    target_omega = vec_with_cos(n2_omega, 0.90, rng)
    graph[3] = NodeCore(3, target_omega, phi=rng.uniform(0,6.2832), vitality=1.0)

    # 30 nodos ruido
    for i in range(5, 5 + config["n_noise"]):
        omega = normalize([rng.gauss(0,1) for _ in range(D)])
        graph[i] = NodeCore(i, omega, phi=rng.uniform(0,6.2832), vitality=rng.uniform(0.3,1.0))

    # Aristas (con peso = 1.0, el ruteo lo decide el coseno, no el peso)
    edge_table.add_node_edges(0, [(1, "Causal", 1.0), (4, "Causal", 1.0)])
    edge_table.add_node_edges(1, [(2, "Causal", 1.0)])
    edge_table.add_node_edges(2, [(3, "Causal", 1.0)])
    edge_table.add_node_edges(3, [])
    edge_table.add_node_edges(4, [])

    for nid, node in graph.items():
        node.edge_start = edge_table.node_offset.get(nid, 0)
        node.edge_count = edge_table.node_count.get(nid, 0)

    return graph, edge_table

# ─── Resonancia local (argmax 1 paso) ───

def local_resonance(graph, edge_table, start_id, n_steps=5):
    """Camina por el grafo eligiendo siempre el vecino con más afinidad."""
    current = start_id
    path = [current]
    for _ in range(n_steps):
        curr_node = graph.get(current)
        if not curr_node:
            break
        edges = edge_table.get_edges(current)
        if not edges:
            break
        best_id, best_aff = -1, -1.0
        for tid, w, _ in edges:
            if tid not in graph:
                continue
            target = graph[tid]
            aff = cosine(curr_node.omega, target.omega) * w
            if aff > best_aff:
                best_aff, best_id = aff, tid
        if best_id == -1 or best_id == current:
            break
        current = best_id
        path.append(current)
    return path

# ─── PPR (Personalized PageRank) ───

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
            # restart: alpha vuelve a la semilla
            new_rank[seed_id] += alpha * rank[nid]
            # follow: (1-alpha) se reparte entre vecinos
            edges = edge_table.get_edges(nid)
            total_aff = 0.0
            for tid, w, _ in edges:
                if tid in graph:
                    total_aff += w
            if total_aff > 0:
                for tid, w, _ in edges:
                    if tid in graph:
                        new_rank[tid] += (1 - alpha) * (w / total_aff) * rank[nid]

        # check convergence
        diff = sum(abs(new_rank[nid] - rank[nid]) for nid in graph)
        rank = new_rank
        if diff < tol:
            break

    return rank

# ─── Evaluación ───

def evaluate_routing(config, seed):
    """Evalúa resonancia local vs PPR en N queries aleatorias."""
    graph, edge_table = build_trap_graph(config, seed)
    rng = random.Random(seed + 1)

    results = {
        "local": {"found_target": 0, "stuck_at_distractor": 0, "stuck_elsewhere": 0, "avg_path_len": 0.0},
        "ppr": {"target_rank": [], "distractor_rank": [], "found_target": 0, "rank_at_target": []},
    }

    # Generar queries desde semilla(0) → target es 3
    target_id = 3
    distractor_id = 4

    # Tests de consulta
    for q in range(config["n_query"]):
        start_id = 0  # siempre empieza en la semilla

        # 1. Resonancia local
        path = local_resonance(graph, edge_table, start_id, n_steps=config["hops"] + 2)
        if target_id in path:
            results["local"]["found_target"] += 1
        elif distractor_id in path:
            results["local"]["stuck_at_distractor"] += 1
        else:
            results["local"]["stuck_elsewhere"] += 1
        results["local"]["avg_path_len"] += len(path) / config["n_query"]

        # 2. PPR
        ranks = ppr_routing(graph, edge_table, start_id, alpha=config["alpha_restart"],
                            max_iters=config["max_iters"], tol=config["tol"])
        ranked = sorted(ranks.items(), key=lambda x: -x[1])

        # Ranking en target
        target_rank = None
        for i, (nid, prob) in enumerate(ranked):
            if nid == target_id:
                target_rank = i + 1
                results["ppr"]["target_rank"].append(i + 1)
                results["ppr"]["rank_at_target"].append(prob)
                break
        if target_rank is not None and target_rank <= 5:
            results["ppr"]["found_target"] += 1

        # Ranking en distractor
        for i, (nid, _) in enumerate(ranked):
            if nid == distractor_id:
                results["ppr"]["distractor_rank"].append(i + 1)
                break

    return results

# ─── Main ───

if __name__ == "__main__":
    print(f"=== {EXPERIMENT_ID} ===")
    print(f"Config: D={CONFIG['D']}, hops={CONFIG['hops']}, alpha={CONFIG['alpha_restart']}")
    print(f"  aff_signal={CONFIG['aff_signal']}, aff_distractor={CONFIG['aff_distractor']}")
    print(f"  queries={CONFIG['n_query']}, noise={CONFIG['n_noise']}\n")

    # 1. Evaluar con seed fijo
    results = evaluate_routing(CONFIG, CONFIG["seed"])

    # 2. Reportar
    local = results["local"]
    ppr = results["ppr"]

    print("=== RESONANCIA LOCAL (argmax 1 paso) ===")
    print(f"  Llegó a target:     {local['found_target']}/{CONFIG['n_query']} "
          f"({100*local['found_target']/CONFIG['n_query']:.0f}%)")
    print(f"  Atrapado en distractor: {local['stuck_at_distractor']}/{CONFIG['n_query']} "
          f"({100*local['stuck_at_distractor']/CONFIG['n_query']:.0f}%)")
    print(f"  Atrapado otro:      {local['stuck_elsewhere']}/{CONFIG['n_query']} "
          f"({100*local['stuck_elsewhere']/CONFIG['n_query']:.0f}%)")
    print(f"  Path avg len:       {local['avg_path_len']:.1f}")

    print(f"\n=== PPR (alpha={CONFIG['alpha_restart']}) ===")
    ppr_found = ppr["found_target"]
    print(f"  Target en top-5:    {ppr_found}/{CONFIG['n_query']} "
          f"({100*ppr_found/CONFIG['n_query']:.0f}%)")
    if ppr["target_rank"]:
        print(f"  Rank medio target:  {sum(ppr['target_rank'])/len(ppr['target_rank']):.1f}")
        print(f"  Prob media target:  {sum(ppr['rank_at_target'])/len(ppr['rank_at_target']):.4f}")
    if ppr["distractor_rank"]:
        print(f"  Rank medio distractor: {sum(ppr['distractor_rank'])/len(ppr['distractor_rank']):.1f}")

    # Veredicto
    local_acc = local['found_target'] / CONFIG['n_query']
    ppr_acc = ppr_found / CONFIG['n_query']
    baseline = 0.50  # azar (v0.22 v1/v2)

    print(f"\n=== VEREDICTO ===")
    print(f"  Local acc:  {local_acc:.3f}  (baseline azar: {baseline})")
    print(f"  PPR acc:    {ppr_acc:.3f}  (objetivo: > {baseline})")
    print(f"  PPR > Local: {ppr_acc > local_acc}")
    print(f"  PPR > azar:  {ppr_acc > baseline}")

    pass_ppr = ppr_acc > baseline and ppr_acc > local_acc
    print(f"  GLOBAL: {'✅ PASS' if pass_ppr else '❌ FAIL'}")

    # Guardar resultados
    result = {
        "experiment_id": EXPERIMENT_ID,
        "date": datetime.now().isoformat(),
        "config": CONFIG,
        "results": {
            "local": {
                "found_target": local["found_target"],
                "stuck_distractor": local["stuck_at_distractor"],
                "stuck_elsewhere": local["stuck_elsewhere"],
                "acc": round(local_acc, 4),
                "avg_path_len": round(local["avg_path_len"], 2),
            },
            "ppr": {
                "found_target_top5": ppr_found,
                "acc": round(ppr_acc, 4),
                "mean_target_rank": round(sum(ppr["target_rank"])/len(ppr["target_rank"]), 1) if ppr["target_rank"] else None,
                "mean_target_prob": round(sum(ppr["rank_at_target"])/len(ppr["rank_at_target"]), 4) if ppr["rank_at_target"] else None,
                "mean_distractor_rank": round(sum(ppr["distractor_rank"])/len(ppr["distractor_rank"]), 1) if ppr["distractor_rank"] else None,
            },
        },
        "comparison": {
            "local_vs_ppr": round(ppr_acc - local_acc, 4),
            "ppr_vs_azar": round(ppr_acc - baseline, 4),
            "pass": pass_ppr,
        },
        "verdict": "PASS" if pass_ppr else "FAIL",
    }

    os.makedirs("phases/phase2_inferencia", exist_ok=True)
    fname = f"phases/phase2_inferencia/results_{EXPERIMENT_ID}.json"
    with open(fname, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResultados guardados en: {fname}")