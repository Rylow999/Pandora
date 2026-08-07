#!/usr/bin/env python3
"""
exp_SGM_0002 - Benchmark memoria NodeCore vs SGMNode

Mide:
  1. Memoria por nodo (bytes) usando sys.getsizeof recursivo
  2. Ticks/segundo (throughput) corriendo N passes
  3. Memoria RSS del proceso

Config: D=16, K=10, seed=42, 50 nodos, 100 edges, 1000 passes
"""

import sys
import gc
import time
import random
import math
import os
import json
from datetime import datetime

# ─── Configuración ───

EXPERIMENT_ID = "exp_SGM_0002_nodecore_memoria_benchmark"

CONFIG = {
    "D": 16,
    "K": 10,
    "seed": 42,
    "n_nodes": 50,
    "n_edges": 100,
    "passes": 1000,
    "beta": 0.10,
    "gamma": 0.01,
    "alpha": 5.0,
    "theta_death": 0.10,
}

# ─── Utilidades ───

def get_size(obj, seen=None):
    """Tamaño recursivo de un objeto Python (bytes)."""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum(get_size(k, seen) + get_size(v, seen) for k, v in obj.items())
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum(get_size(i, seen) for i in obj)
    return size

def get_rss_mb():
    """Memoria RSS del proceso actual en MB."""
    try:
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) / 1024.0  # KB -> MB
    except:
        pass
    return 0.0

def normalize(v):
    norm_sq = sum(x*x for x in v)
    if norm_sq == 0: return v
    norm = math.sqrt(norm_sq)
    return [x/norm for x in v]

# ─── SGMNode (v1.3 - referencia) ───

class SGMNode:
    __slots__ = ['id', 'omega', 'phase', 'vitality', 'connections']
    def __init__(self, node_id, omega, phase=0.0, vitality=1.0):
        self.id = node_id
        self.omega = list(omega)
        self.phase = phase
        self.vitality = vitality
        self.connections = []

class SGMEngine:
    def __init__(self, config):
        self.config = config
        self.nodes = {}
        self.threads = []
        self.rng = random.Random(config["seed"])
        self.tick = 0

    def build_corpus_graph(self, n_nodes, n_edges):
        D = self.config["D"]
        for i in range(n_nodes):
            omega = normalize([self.rng.gauss(0, 1) for _ in range(D)])
            self.nodes[i] = SGMNode(i, omega,
                                    phase=self.rng.uniform(0, 6.2832),
                                    vitality=self.rng.uniform(0.3, 1.0))
        for _ in range(n_edges):
            a = self.rng.randint(0, n_nodes-1)
            b = self.rng.randint(0, n_nodes-1)
            if a != b:
                w = self.rng.uniform(0.3, 1.0)
                self.nodes[a].connections.append((b, w, "Causal"))
        for k in range(self.config["K"]):
            start = self.rng.randint(0, n_nodes-1)
            self.threads.append({"id": k, "current_node": start})

    def step(self):
        beta = self.config["beta"]
        gamma = self.config["gamma"]
        theta_death = self.config["theta_death"]

        for thread in self.threads:
            curr = self.nodes[thread["current_node"]]
            affinities = []
            for target_id, weight, conn_type in curr.connections:
                target = self.nodes[target_id]
                aff = sum(x*y for x,y in zip(curr.omega, target.omega))
                affinities.append((target_id, aff * weight))
            if affinities:
                affinities.sort(key=lambda x: x[1], reverse=True)
                top_id = affinities[0][0]
                thread["current_node"] = top_id
                visited = self.nodes[top_id]
                r = 0.5
                for i in range(len(visited.omega)):
                    visited.omega[i] = (1 - beta) * visited.omega[i] + beta * r
                norm = math.sqrt(sum(x*x for x in visited.omega))
                if norm > 0:
                    visited.omega = [x/norm for x in visited.omega]
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

# ─── NodeCore (v1.4 - cuantizado) ───

class NodeCore:
    __slots__ = ['id', 'omega', 'phi_u16', 'v_u16', 'flags', 'edge_start', 'edge_count']
    def __init__(self, node_id, omega, phi=0.0, vitality=1.0):
        self.id = node_id
        self.omega = [round(x, 4) for x in omega]  # f16 approx
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
            omega = normalize([self.rng.gauss(0, 1) for _ in range(D)])
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
                self.edge_table.node_offset.pop(nid, None)
                self.edge_table.node_count.pop(nid, None)
                for t in self.threads:
                    if t["current_node"] == nid:
                        t["current_node"] = random.choice(list(self.nodes.keys())) if self.nodes else 0

        self.tick += 1
        return pruned

    def run(self, n_ticks):
        for _ in range(n_ticks):
            self.step()

# ─── Benchmark runner ───

def run_benchmark(engine_class, name, config):
    """Corre el benchmark y devuelve métricas."""
    gc.collect()
    rss_before = get_rss_mb()
    
    engine = engine_class(config)
    engine.build_corpus_graph(config["n_nodes"], config["n_edges"])
    
    # Memoria después de construir
    gc.collect()
    rss_after_build = get_rss_mb()
    
    # Medir tamaño de estructuras
    total_nodes_size = sum(get_size(node) for node in engine.nodes.values())
    if hasattr(engine, 'edge_table'):
        edges_size = get_size(engine.edge_table)
    else:
        edges_size = sum(get_size(node.connections) for node in engine.nodes.values())
    
    total_struct_size = total_nodes_size + edges_size
    bytes_per_node = total_struct_size / len(engine.nodes) if engine.nodes else 0
    
    # Warmup
    engine.run(10)
    
    # Benchmark real
    start_time = time.perf_counter()
    engine.run(config["passes"])
    elapsed = time.perf_counter() - start_time
    
    ticks_per_sec = config["passes"] / elapsed if elapsed > 0 else 0
    
    gc.collect()
    rss_after_run = get_rss_mb()
    
    return {
        "engine": name,
        "config": {k: v for k, v in config.items() if k != "seed"},
        "nodes_count": len(engine.nodes),
        "edges_count": len(engine.edge_table.all_edges) if hasattr(engine, 'edge_table') else sum(len(n.connections) for n in engine.nodes.values()),
        "struct_size_bytes": total_struct_size,
        "bytes_per_node": round(bytes_per_node, 2),
        "ticks_per_second": round(ticks_per_sec, 2),
        "elapsed_seconds": round(elapsed, 4),
        "rss_before_mb": round(rss_before, 2),
        "rss_after_build_mb": round(rss_after_build, 2),
        "rss_after_run_mb": round(rss_after_run, 2),
        "rss_delta_mb": round(rss_after_run - rss_before, 2),
    }

# ─── Main ───

if __name__ == "__main__":
    print(f"=== exp_SGM_0002: Benchmark Memoria NodeCore vs SGMNode ===")
    print(f"Config: D={CONFIG['D']}, K={CONFIG['K']}, nodes={CONFIG['n_nodes']}, edges={CONFIG['n_edges']}, passes={CONFIG['passes']}")
    print(f"Seed: {CONFIG['seed']}\n")
    
    # 1. SGMNode (referencia v1.3)
    print("[1/2] Corriendo SGMNode (v1.3 floats puros)...")
    sgm_result = run_benchmark(SGMEngine, "SGMNode_v1.3", CONFIG)
    
    # 2. NodeCore (v1.4 cuantizado)
    print("[2/2] Corriendo NodeCore (v1.4 f16+u16+CSR)...")
    nc_result = run_benchmark(NodeCoreEngine, "NodeCore_v1.4", CONFIG)
    
    # 3. Comparación
    print("\n=== RESULTADOS ===")
    print(f"{'Métrica':<30} {'SGMNode v1.3':>15} {'NodeCore v1.4':>15} {'Ratio':>10}")
    print("-" * 70)
    
    # Bytes por nodo
    ratio_mem = sgm_result["bytes_per_node"] / nc_result["bytes_per_node"] if nc_result["bytes_per_node"] > 0 else 0
    print(f"{'Bytes/nodo (struct)':<30} {sgm_result['bytes_per_node']:>15.1f} {nc_result['bytes_per_node']:>15.1f} {ratio_mem:>9.2f}x")
    
    # Ticks/seg
    ratio_tps = nc_result["ticks_per_second"] / sgm_result["ticks_per_second"] if sgm_result["ticks_per_second"] > 0 else 0
    print(f"{'Ticks/seg':<30} {sgm_result['ticks_per_second']:>15.1f} {nc_result['ticks_per_second']:>15.1f} {ratio_tps:>9.2f}x")
    
    # RSS
    print(f"{'RSS delta (MB)':<30} {sgm_result['rss_delta_mb']:>15.1f} {nc_result['rss_delta_mb']:>15.1f} {'-':>10}")
    
    # Veredicto
    mem_ok = ratio_mem >= 2.5  # objetivo ~3.5x, aceptamos >=2.5x
    speed_ok = ratio_tps >= 0.8  # NodeCore no más lento que 80% de SGMNode
    
    print(f"\n=== VEREDICTO ===")
    print(f"Memoria:     {'✅ PASS' if mem_ok else '❌ FAIL'} (ratio {ratio_mem:.2f}x, objetivo ≥2.5x)")
    print(f"Velocidad:   {'✅ PASS' if speed_ok else '❌ FAIL'} (ratio {ratio_tps:.2f}x, objetivo ≥0.8x)")
    print(f"GLOBAL:      {'✅ PASS' if (mem_ok and speed_ok) else '❌ FAIL'}")
    
    # 4. Guardar resultados
    result = {
        "experiment_id": EXPERIMENT_ID,
        "date": datetime.now().isoformat(),
        "config": CONFIG,
        "sgmnode": sgm_result,
        "nodecore": nc_result,
        "comparison": {
            "memory_ratio": round(ratio_mem, 2),
            "speed_ratio": round(ratio_tps, 2),
            "memory_pass": mem_ok,
            "speed_pass": speed_ok,
            "global_pass": mem_ok and speed_ok,
        },
        "verdict": "PASS" if (mem_ok and speed_ok) else "FAIL",
    }
    
    os.makedirs("phases/phase0_substrato", exist_ok=True)
    results_file = f"phases/phase0_substrato/results_{EXPERIMENT_ID}.json"
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResultados guardados en: {results_file}")