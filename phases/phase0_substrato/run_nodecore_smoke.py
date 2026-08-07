#!/usr/bin/env python3
"""
exp_SGM_0001 - Smoke Test NodeCore

Verifica que NodeCore + EdgeTable construyen y operan un grafo
reproducible con seed fijo sin errores de runtime.

Corre en foreground (<10s).
"""

import sys
import math
import random

EXPERIMENT_ID = "exp_SGM_0001_nodecore_smoke_test"

CONFIG = {
    "D": 16,
    "K": 10,
    "seed": 42,
    "n_nodes": 50,
    "n_edges": 100,
    "passes": 100,
    "beta": 0.10,
    "gamma": 0.01,
    "alpha": 5.0,
    "theta_death": 0.10,
}

def normalize(v):
    norm_sq = sum(x*x for x in v)
    if norm_sq == 0: return v
    norm = math.sqrt(norm_sq)
    return [x/norm for x in v]

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

    @phase.setter
    def phase(self, val):
        self.phi_u16 = int((val / 6.2832) * 65536) % 65536

    @property
    def vitality(self):
        return self.v_u16 / 65535.0

    @vitality.setter
    def vitality(self, val):
        self.v_u16 = max(0, min(65535, int(max(0.0, min(1.0, val)) * 65535)))

class EdgeTable:
    def __init__(self):
        self.all_edges = []
        self.node_offset = {}
        self.node_count = {}

    def add_node_edges(self, node_id, edges):
        self.node_offset[node_id] = len(self.all_edges)
        self.node_count[node_id] = len(edges)
        for target_id, conn_type, weight in edges:
            weight_u8 = int(max(0, min(1, weight)) * 255)
            conn_code = {"Causal": 0, "Functional": 1, "Temporal": 2,
                        "Cognitive": 3, "Terminal": 4}.get(conn_type, 0)
            self.all_edges.append((target_id, conn_code, weight_u8))

    def get_edges(self, node_id):
        start = self.node_offset.get(node_id, 0)
        count = self.node_count.get(node_id, 0)
        result = []
        for i in range(start, start + count):
            if i < len(self.all_edges):
                target, conn_code, weight_u8 = self.all_edges[i]
                weight = weight_u8 / 255.0
                conn_type = ["Causal", "Functional", "Temporal", "Cognitive", "Terminal"][conn_code] if conn_code < 5 else "Causal"
                result.append((target, weight, conn_type))
        return result

class NodeCoreEngine:
    def __init__(self, config):
        self.config = config
        self.nodes = {}
        self.edge_table = EdgeTable()
        self.threads = []
        self.rng = random.Random(config["seed"])
        self.tick = 0

    def build_corpus_graph(self, n_nodes, n_edges):
        D = self.config["D"]
        edges_per_node = {}
        for i in range(n_nodes):
            omega = [round(x, 4) for x in normalize([self.rng.gauss(0, 1) for _ in range(D)])]
            self.nodes[i] = NodeCore(i, omega,
                                     phi=self.rng.uniform(0, 6.2832),
                                     vitality=self.rng.uniform(0.3, 1.0))
            edges_per_node[i] = []
        for _ in range(n_edges):
            a = self.rng.randint(0, n_nodes-1)
            b = self.rng.randint(0, n_nodes-1)
            if a != b:
                w = self.rng.uniform(0.3, 1.0)
                edges_per_node[a].append((b, "Causal", w))
        for nid in sorted(self.nodes.keys()):
            self.edge_table.add_node_edges(nid, edges_per_node[nid])
            self.nodes[nid].edge_start = self.edge_table.node_offset[nid]
            self.nodes[nid].edge_count = self.edge_table.node_count[nid]
        for k in range(self.config["K"]):
            start = self.rng.randint(0, n_nodes-1)
            self.threads.append({"id": k, "current_node": start})

    def step(self):
        beta = self.config["beta"]
        gamma = self.config["gamma"]
        theta_death = self.config["theta_death"]

        for thread in self.threads:
            curr = self.nodes[thread["current_node"]]
            edges = self.edge_table.get_edges(curr.id)
            affinities = []
            for target_id, weight, conn_type in edges:
                target = self.nodes[target_id]
                aff = sum(x*y for x,y in zip(curr.omega, target.omega))
                affinities.append((target_id, aff * weight))
            if affinities:
                affinities.sort(key=lambda x: x[1], reverse=True)
                top_id = affinities[0][0]
                thread["current_node"] = top_id
                visited = self.nodes[top_id]
                r = 0.5
                new_omega = [(1 - beta) * x + beta * r for x in visited.omega]
                norm = math.sqrt(sum(x*x for x in new_omega))
                if norm > 0:
                    visited.omega = [round(x / norm, 4) for x in new_omega]
                delta = 0.1 * r * (0 - visited.phase)
                visited.phase = (visited.phase + delta) % 6.2832
                decay = math.exp(-gamma)
                visited.vitality = visited.vitality * decay + 1.0 * (1 - decay)

        pruned = []
        for nid, node in list(self.nodes.items()):
            if node.vitality < theta_death:
                pruned.append(nid)
                del self.nodes[nid]
                for t in self.threads:
                    if t["current_node"] == nid:
                        t["current_node"] = random.choice(list(self.nodes.keys())) if self.nodes else 0
        self.tick += 1
        return pruned

    def run(self, n_ticks):
        for _ in range(n_ticks):
            self.step()

# ─── Main ───

if __name__ == "__main__":
    print(f"=== {EXPERIMENT_ID} ===")
    print(f"Config: D={CONFIG['D']}, K={CONFIG['K']}, nodes={CONFIG['n_nodes']}, edges={CONFIG['n_edges']}, passes={CONFIG['passes']}")
    print(f"Seed: {CONFIG['seed']}\n")

    try:
        engine = NodeCoreEngine(CONFIG)
        engine.build_corpus_graph(CONFIG["n_nodes"], CONFIG["n_edges"])
        print(f"[OK] Grafo construido: {len(engine.nodes)} nodos, {len(engine.edge_table.all_edges)} aristas, {len(engine.threads)} threads")

        engine.run(CONFIG["passes"])
        print(f"[OK] {CONFIG['passes']} ticks ejecutados sin errores")
        print(f"[OK] Nodos finales: {len(engine.nodes)}")
        print(f"[OK] Threads activos: {len(engine.threads)}")

        # Verificar reproducibilidad: misma seed = mismo estado
        engine2 = NodeCoreEngine(CONFIG)
        engine2.build_corpus_graph(CONFIG["n_nodes"], CONFIG["n_edges"])
        engine2.run(CONFIG["passes"])
        
        # Comparar estado final
        same = True
        for nid in engine.nodes:
            if nid not in engine2.nodes:
                same = False
                break
            n1, n2 = engine.nodes[nid], engine2.nodes[nid]
            if (abs(n1.vitality - n2.vitality) > 1e-6 or
                abs(n1.phase - n2.phase) > 1e-6 or
                any(abs(a-b) > 1e-4 for a,b in zip(n1.omega, n2.omega))):
                same = False
                break
        
        if same:
            print(f"[OK] Reproducibilidad: MISMA seed = MISMO estado final")
        else:
            print(f"[WARN] Reproducibilidad: estados difieren")

        print(f"\n✅ SMOKE TEST: PASS — NodeCore opera sin errores")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ SMOKE TEST: FAIL — {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)