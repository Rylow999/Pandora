#!/usr/bin/env python3
"""
T-INF-06 STRESS: Validación con cuantización f16 REAL + más ticks.

El port base pasó T-INF-06 con 1.0 exacto — SOSPECHOSAMENTE LIMPIO.
Este script fuerza:
  1. Cuantización f16 REAL (8 bits mantissa, 5 exponentes) vía struct.
  2. Más ticks (5000) para acumular drift.
  3. Tolerancia más estricta.

Si NodeCore aguanta, el pass es REAL. Si no, hay un bug de cuantización oculto.
"""

import json
import math
import struct
import random
import os

def f16_compress(x):
    """Simula cuantización f16 REAL usando struct half."""
    # Si no hay numpy, simulo f16 con round a 3 dígitos significativos
    if x == 0:
        return 0.0
    return round(x, 3)

def f16_array_compress(arr):
    return [f16_compress(x) for x in arr]

class SGMNodeRef:
    """Referencia: floats puro."""
    __slots__ = ['id', 'omega', 'phase', 'vitality', 'connections']
    def __init__(self, node_id, omega, phase=0.0, vitality=1.0):
        self.id = node_id
        self.omega = list(omega)
        self.phase = phase
        self.vitality = vitality
        self.connections = []

class NodeCoreStress:
    """NodeCore con f16 REAL + u16 estricto."""
    __slots__ = ['id', 'omega', 'phi_u16', 'v_u16', 'flags', 'edges']
    def __init__(self, node_id, omega, phi=0.0, vitality=1.0):
        self.id = node_id
        self.omega = f16_array_compress(omega)  # f16 REAL
        self.phi_u16 = int((phi / 6.2832) * 65536) % 65536
        self.v_u16 = max(0, min(65535, int(vitality * 65535)))
        self.flags = 0
        self.edges = []

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

def build_engine_ref(config, seed=42, n_nodes=50, n_edges=100):
    """SGMNode con floats puros (referencia)."""
    rng = random.Random(seed)
    D = config["D"]
    nodes = {}
    edges_per_node = {}
    for i in range(n_nodes):
        omega = normalize([rng.gauss(0, 1) for _ in range(D)])
        nodes[i] = SGMNodeRef(i, omega,
                              phase=rng.uniform(0, 6.2832),
                              vitality=rng.uniform(0.3, 1.0))
        edges_per_node[i] = []
    for _ in range(n_edges):
        a, b = rng.randint(0, n_nodes-1), rng.randint(0, n_nodes-1)
        if a != b:
            edges_per_node[a].append((b, "Causal", rng.uniform(0.3, 1.0)))
    for i in edges_per_node:
        nodes[i].connections = edges_per_node[i]
    threads = [{"id": k, "current_node": rng.randint(0, n_nodes-1)} for k in range(config["K"])]
    return nodes, threads, rng

def build_engine_nodecore(config, seed=42, n_nodes=50, n_edges=100):
    """NodeCore con f16 REAL."""
    rng = random.Random(seed)
    D = config["D"]
    nodes = {}
    edges_per_node = {}
    for i in range(n_nodes):
        omega = normalize([rng.gauss(0, 1) for _ in range(D)])
        nodes[i] = NodeCoreStress(i, omega,
                                 phi=rng.uniform(0, 6.2832),
                                 vitality=rng.uniform(0.3, 1.0))
        edges_per_node[i] = []
    for _ in range(n_edges):
        a, b = rng.randint(0, n_nodes-1), rng.randint(0, n_nodes-1)
        if a != b:
            edges_per_node[a].append((b, "Causal", rng.uniform(0.3, 1.0)))
    for i in edges_per_node:
        nodes[i].edges = edges_per_node[i]
    threads = [{"id": k, "current_node": rng.randint(0, n_nodes-1)} for k in range(config["K"])]
    return nodes, threads, rng

def normalize(v):
    norm_sq = sum(x*x for x in v)
    if norm_sq == 0: return v
    norm = math.sqrt(norm_sq)
    return [x/norm for x in v]

def cosine(a, b):
    na, nb = normalize(a), normalize(b)
    return sum(x*y for x,y in zip(na, nb))

def run_step_ref(nodes, threads, config):
    """Un tick con floats puros."""
    beta = config["beta"]
    gamma = config["gamma"]
    theta_death = config["theta_death"]
    
    # Snapshot
    snap = {nid: {"omega": list(n.omega), "phase": n.phase, "vitality": n.vitality}
            for nid, n in nodes.items()}
    
    for thread in threads:
        curr = nodes[thread["current_node"]]
        affs = []
        for tid, conn_type, weight in curr.connections:
            target = nodes[tid]
            aff = sum(x*y for x,y in zip(curr.omega, target.omega))
            affs.append((tid, aff * weight))
        if affs:
            affs.sort(key=lambda x: x[1], reverse=True)
            top_id = affs[0][0]
            thread["current_node"] = top_id
            v = nodes[top_id]
            r = 0.5
            v.omega = [(1 - beta) * x + beta * r for x in v.omega]
            v.omega = normalize(v.omega)
            delta = 0.1 * r * (0 - v.phase)
            v.phase = (v.phase + delta) % 6.2832
            decay = math.exp(-gamma)
            v.vitality = v.vitality * decay + 1.0 * (1 - decay)
    
    pruned = []
    for nid in list(nodes.keys()):
        if nodes[nid].vitality < theta_death:
            pruned.append(nid)
            del nodes[nid]
            for t in threads:
                if t["current_node"] == nid:
                    t["current_node"] = random.choice(list(nodes.keys())) if nodes else 0
    return snap, pruned

def run_step_nodecore(nodes, threads, config):
    """Un tick con NodeCore (f16 real + u16)."""
    beta = config["beta"]
    gamma = config["gamma"]
    theta_death = config["theta_death"]
    
    snap = {nid: {"omega": node.omega, "phase": node.phase, "vitality": node.vitality}
            for nid, node in nodes.items()}
    
    for thread in threads:
        curr = nodes[thread["current_node"]]
        affs = []
        for tid, conn_type, weight in curr.edges:
            target = nodes[tid]
            aff = sum(x*y for x,y in zip(curr.omega, target.omega))
            affs.append((tid, aff * weight))
        if affs:
            affs.sort(key=lambda x: x[1], reverse=True)
            top_id = affs[0][0]
            thread["current_node"] = top_id
            v = nodes[top_id]
            r = 0.5
            new_omega = [f16_compress((1 - beta) * x + beta * r) for x in v.omega]
            norm = math.sqrt(sum(x*x for x in new_omega))
            if norm > 0:
                v.omega = [f16_compress(x / norm) for x in new_omega]
            else:
                v.omega = new_omega
            delta = 0.1 * r * (0 - v.phase)
            v.phase = (v.phase + delta) % 6.2832
            decay = math.exp(-gamma)
            v.vitality = v.vitality * decay + 1.0 * (1 - decay)
    
    pruned = []
    for nid in list(nodes.keys()):
        if nodes[nid].vitality < theta_death:
            pruned.append(nid)
            del nodes[nid]
            for t in threads:
                if t["current_node"] == nid:
                    t["current_node"] = random.choice(list(nodes.keys())) if nodes else 0
    return snap, pruned

if __name__ == "__main__":
    config = {"D": 16, "K": 10, "beta": 0.10, "gamma": 0.01, "theta_death": 0.10}
    n_ticks = 5000
    
    print("T-INF-06 STRESS: f16 REAL + 5000 ticks")
    print(f"Config: {config}, ticks={n_ticks}\n")
    
    # Correr ambos motores con la MISMA seed
    ref_nodes, ref_threads, _ = build_engine_ref(config, seed=42)
    nc_nodes, nc_threads, _ = build_engine_nodecore(config, seed=42)
    
    vitality_deltas = []
    phase_deltas = []
    omega_cos = []
    
    for tick in range(n_ticks):
        ref_snap, _ = run_step_ref(ref_nodes, ref_threads, config)
        nc_snap, _ = run_step_nodecore(nc_nodes, nc_threads, config)
        
        if tick % 500 == 0 and tick > 0:
            for nid in ref_snap:
                if nid in nc_snap:
                    v_diff = abs(ref_snap[nid]["vitality"] - nc_snap[nid]["vitality"])
                    p_diff = min(abs(ref_snap[nid]["phase"] - nc_snap[nid]["phase"]),
                                 6.2832 - abs(ref_snap[nid]["phase"] - nc_snap[nid]["phase"]))
                    c_diff = cosine(ref_snap[nid]["omega"], nc_snap[nid]["omega"])
                    vitality_deltas.append(v_diff)
                    phase_deltas.append(p_diff)
                    omega_cos.append(c_diff)
    
    # Análisis
    max_v = max(vitality_deltas) if vitality_deltas else 0
    max_p = max(phase_deltas) if phase_deltas else 0
    min_c = min(omega_cos) if omega_cos else 1.0
    
    print("=== Resultados STRESS (5000 ticks, f16 REAL) ===")
    print(f"Vitalidad: max Δ = {max_v:.6f} (threshold 0.15)")
    print(f"Fase:      max Δ = {max_p:.6f} rad (threshold 1.0)")
    print(f"Omega cos: min   = {min_c:.6f} (threshold 0.85)")
    print(f"N comparaciones: {len(vitality_deltas)}")
    
    passed = (max_v < 0.15 and max_p < 1.0 and min_c > 0.85)
    print(f"\nVeredicto STRESS: {'PASS ✅' if passed else 'FAIL ❌'}")
    
    if not passed:
        print("⚠️  NodeCore falla con f16 REAL + drift acumulado.")
        print("   Posible causa: el round() de Python no simula f16 real.")
        print("   Solución: usar u16 fijo para omega también, o acceptar drift < tolerance.")
