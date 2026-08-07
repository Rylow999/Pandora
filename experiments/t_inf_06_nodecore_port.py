#!/usr/bin/env python3
"""
T-INF-06: Equivalencia SGMNode (v1.3) vs NodeCore+EdgeTable (v1.4)

Este script corre el test de equivalencia. Si NodeCore no existe, usa SGMNode como
baseline y graba snapshots. Si NodeCore existe, carga los snapshots del baseline
y verifica equivalencia dentro de la tolerancia de cuantización.

Regla del protocolo: este test se escribió ANTES de migrar a NodeCore.
El baseline SGMNode corrió primero (exp_SGM_0003), grabó snapshots.
Ahora NodeCore debe cargar esos snapshots y reproducirlos.
"""

import json
import sys
import os
import random
import math
from datetime import datetime

# ─── Configuración del experimento ───

EXPERIMENT_ID = "exp_SGM_0003_nodecore_equiv_teorica"

# Hyperparámetros según SGM v1.4 §7 + LANGUAGE-ENGINE v0.14d
CONFIG = {
    "D": 16,
    "K": 10,
    "seed": 42,
    "passes": 1000,
    "beta": 0.10,
    "gamma": 0.01,
    "alpha": 5.0,
    "theta_death": 0.10,
    "tol_vitality": 0.15,
    "tol_phase": 1.0,
    "tol_omega_cos": 0.85,
}

TOLERANCE = 0.15

# ─── Utilidades vectoriales (Python puro, no numpy) ───

def normalize(v):
    norm_sq = sum(x*x for x in v)
    if norm_sq == 0:
        return v
    norm = math.sqrt(norm_sq)
    return [x/norm for x in v]

def cosine(a, b):
    na = normalize(a)
    nb = normalize(b)
    return sum(x*y for x,y in zip(na, nb))

def vec_add(a, b, sa=1.0, sb=1.0):
    return [sa*x + sb*y for x,y in zip(a, b)]

def vec_scale(a, s):
    return [x*s for x in a]

def vec_norm(a):
    return math.sqrt(sum(x*x for x in a))

# ─── SGMNode (v1.3 — referencia, floats f32) ───

class SGMNode:
    """Representación original v1.3: omega=Vec<f32>, phi=f32, V=f32."""
    __slots__ = ['id', 'omega', 'phase', 'vitality', 'connections']
    
    def __init__(self, node_id, omega, phase=0.0, vitality=1.0):
        self.id = node_id
        self.omega = list(omega)
        self.phase = phase
        self.vitality = vitality
        self.connections = []  # [(target_id, weight, conn_type)]

class SGMEngine:
    """Motor SGM con SGMNode (v1.3). Usa Ec.1-5, reward fijo para test determinista."""
    def __init__(self, config):
        self.config = config
        self.nodes = {}
        self.threads = []
        self.rng = random.Random(config["seed"])
        self.tick = 0

    def build_corpus_graph(self, n_nodes=50, n_edges=100):
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
        """Un tick: mover cadenas (Ec.2), update ω (Ec.1), φ (Ec.3), V (Ec.5), poda (θ_death)."""
        beta = self.config["beta"]
        gamma = self.config["gamma"]
        theta_death = self.config["theta_death"]

        # Snapshot antes del tick (para comparación)
        snapshot = {nid: {"omega": list(node.omega), "phase": node.phase,
                          "vitality": node.vitality} for nid, node in self.nodes.items()}

        # 1. Mover cadenas por afinidad (Ec.2 boost)
        for thread in self.threads:
            curr = self.nodes[thread["current_node"]]
            affinities = []
            for target_id, weight, conn_type in curr.connections:
                target = self.nodes[target_id]
                aff = sum(x*y for x,y in zip(curr.omega, target.omega))
                affinities.append((target_id, aff * weight))  # boost por peso
            
            if affinidades:
                affinities.sort(key=lambda x: x[1], reverse=True)
                top_id = affinities[0][0]
                thread["current_node"] = top_id
                visited = self.nodes[top_id]
                
                # 2. Update ω (Ec.1): TD-learning, reward fijo
                r = 0.5
                for i in range(len(visited.omega)):
                    visited.omega[i] = (1 - beta) * visited.omega[i] + beta * r
                visited.omega = normalize(visited.omega)
                
                # 3. Update φ (Ec.3): Kuramoto simplificado, θ_a=0
                delta = 0.1 * r * (0 - visited.phase)
                visited.phase = (visited.phase + delta) % 6.2832
                
                # 4. Update V (Ec.5): decaimiento exponencial
                A = 1.0
                decay = math.exp(-gamma)
                visited.vitality = visited.vitality * decay + A * (1 - decay)

        # 5. Poda (vitalidad < θ_death)
        pruned = []
        for nid, node in list(self.nodes.items()):
            if node.vitality < theta_death:
                pruned.append(nid)
                del self.nodes[nid]
                for t in self.threads:
                    if t["current_node"] == nid:
                        t["current_node"] = random.choice(list(self.nodes.keys())) if self.nodes else 0

        self.tick += 1
        return snapshot, pruned

    def run(self, n_ticks):
        snapshots = []
        for i in range(n_ticks):
            snap, pruned = self.step()
            if i % 100 == 0:
                snapshots.append({
                    "tick": self.tick,
                    "nodes": {nid: {"omega": s["omega"], "phase": s["phase"],
                                   "vitality": s["vitality"]} for nid, s in snap.items()},
                    "pruned": pruned,
                    "threads": [{"current_node": t["current_node"], "id": t["id"]}
                               for t in self.threads],
                })
        return snapshots


# ─── NodeCore (v1.4 — cuantizado, layout CSR) ───
# ESTE ES EL PORT QUE DEBE PASAR T-INF-06

class NodeCore:
    """
    SGM v1.4 §6.1: NodeCore con 4 campos cuantizados.
    
    - omega: list[f16]  → en Python se simula con float (precision limitada)
                         Pero el CONCEPTO es f16: 128 bytes (D=64) vs 256 bytes f32.
    - phi:   u16        → punto fijo 0..65535 → 0..2π
    - v:     u16        → punto fijo 0..65535 → 0.0..1.0
    - flags: u8         → bitfield: is_terminal + state + sensor_origin
    
    EdgeTable (§6.3): aristas en array plano tipo CSR, no Vec por nodo.
    """
    __slots__ = ['id', 'omega', 'phi_u16', 'v_u16', 'flags', 'edge_start', 'edge_count']
    
    def __init__(self, node_id, omega, phi=0.0, vitality=1.0):
        self.id = node_id
        # f16: simulo con round a 4 decimales (precision f16 ~3-4 dígitos significativos)
        self.omega = [round(x, 4) for x in omega]  # f16 approximation
        # u16 fijo: phi ∈ [0, 2π) → [0, 65535]
        self.phi_u16 = int((phi / 6.2832) * 65536) % 65536
        # u16 fijo: vitality ∈ [0, 1] → [0, 65535]
        self.v_u16 = int(vitality * 65535) if vitality >= 0 else 0
        self.v_u16 = min(self.v_u16, 65535)
        # flags: 4 bits → state, 1 bit → terminal, 1 bit → sensor_origin
        self.flags = 0  # 0 = Active
        # CSR: índices en EdgeTable global
        self.edge_start = 0
        self.edge_count = 0

    @property
    def phase(self):
        """Decodifica phi de u16 a [0, 2π)."""
        return (self.phi_u16 / 65536.0) * 6.2832

    @phase.setter
    def phase(self, val):
        self.phi_u16 = int((val / 6.2832) * 65536) % 65536

    @property
    def vitality(self):
        """Decodifica vitality de u16 a [0, 1]."""
        return self.v_u16 / 65535.0

    @vitality.setter
    def vitality(self, val):
        v = max(0.0, min(1.0, val))
        self.v_u16 = int(v * 65535)

    @property
    def omega_f32(self):
        """Omega como float32 (para comparación con SGMNode)."""
        return [float(x) for x in self.omega]  # f16 → f32


class EdgeTable:
    """
    SGM v1.4 §6.3: aristas en array plano, estilo CSR.
    
    Edge struct: target(u32), conn_type(u8), weight(u8 cuantizado 0-255)
    Cada nodo: edge_start (índice en all_edges), edge_count (número de aristas).
    """
    def __init__(self):
        self.all_edges = []       # [(target_id, conn_type_code, weight_u8)]
        self.node_offset = {}     # {node_id: índice de inicio}
        self.node_count = {}      # {node_id: número de aristas}
    
    def add_node_edges(self, node_id, edges):
        """edges = [(target_id, conn_type, weight_float)]"""
        self.node_offset[node_id] = len(self.all_edges)
        self.node_count[node_id] = len(edges)
        for target_id, conn_type, weight in edges:
            weight_u8 = int(max(0, min(1, weight)) * 255)  # float → u8
            conn_code = {"Causal": 0, "Functional": 1, "Temporal": 2,
                        "Cognitive": 3, "Terminal": 4}.get(conn_type, 0)
            self.all_edges.append((target_id, conn_code, weight_u8))
    
    def get_edges(self, node_id):
        """Devuelve las aristas de un nodo como [(target_id, weight_float, conn_type)]."""
        start = self.node_offset.get(node_id, 0)
        count = self.node_count.get(node_id, 0)
        result = []
        for i in range(start, start + count):
            if i < len(self.all_edges):
                target, conn_code, weight_u8 = self.all_edges[i]
                weight = weight_u8 / 255.0  # u8 → float
                conn_type = ["Causal", "Functional", "Temporal", "Cognitive", "Terminal"][conn_code] if conn_code < 5 else "Causal"
                result.append((target, weight, conn_type))
        return result


class NodeCoreEngine:
    """Motor SGM con NodeCore + EdgeTable (v1.4). Misma lógica que SGMEngine pero cuantizado."""
    
    def __init__(self, config):
        self.config = config
        self.nodes = {}
        self.edge_table = EdgeTable()
        self.threads = []
        self.rng = random.Random(config["seed"])
        self.tick = 0

    def build_corpus_graph(self, n_nodes=50, n_edges=100):
        """Construye el mismo grafo que SGMEngine.build_corpus_graph."""
        D = self.config["D"]
        # Primero construyo todos los nodos
        edges_per_node = {}
        for i in range(n_nodes):
            omega = normalize([self.rng.gauss(0, 1) for _ in range(D)])
            # f16: simulo redondeando a 4 decimales
            omega_f16 = [round(x, 4) for x in omega]
            self.nodes[i] = NodeCore(i, omega,
                                     phi=self.rng.uniform(0, 6.2832),
                                     vitality=self.rng.uniform(0.3, 1.0))
            edges_per_node[i] = []
        
        # Luego las aristas (mismo seed → mismo grafo)
        for _ in range(n_edges):
            a = self.rng.randint(0, n_nodes-1)
            b = self.rng.randint(0, n_nodes-1)
            if a != b:
                w = self.rng.uniform(0.3, 1.0)
                edges_per_node[a].append((b, "Causal", w))
        
        # Construir EdgeTable CSR
        for nid in sorted(self.nodes.keys()):
            self.edge_table.add_node_edges(nid, edges_per_node[nid])
            self.nodes[nid].edge_start = self.edge_table.node_offset[nid]
            self.nodes[nid].edge_count = self.edge_table.node_count[nid]
        
        # Threads (misma inicialización)
        for k in range(self.config["K"]):
            start = self.rng.randint(0, n_nodes-1)
            self.threads.append({"id": k, "current_node": start})

    def step(self):
        """Mismo tick que SGMEngine, pero usando NodeCore + EdgeTable (cuantizado)."""
        beta = self.config["beta"]
        gamma = self.config["gamma"]
        theta_death = self.config["theta_death"]

        # Snapshot ANTES del tick
        snapshot = {nid: {"omega": node.omega_f32, "phase": node.phase,
                          "vitality": node.vitality} for nid, node in self.nodes.items()}

        # 1. Mover cadenas por afinidad (Ec.2 boost sobre EdgeTable)
        for thread in self.threads:
            curr = self.nodes[thread["current_node"]]
            edges = self.edge_table.get_edges(curr.id)
            
            affinities = []
            for target_id, weight, conn_type in edges:
                target = self.nodes[target_id]
                # coseno sobre omega (ambos normalizados aproximadamente)
                aff = sum(x*y for x,y in zip(curr.omega_f32, target.omega_f32))
                affinities.append((target_id, aff * weight))
            
            if affinities:
                affinities.sort(key=lambda x: x[1], reverse=True)
                top_id = affinities[0][0]
                thread["current_node"] = top_id
                visited = self.nodes[top_id]
                
                # 2. Update ω (Ec.1): TD-learning con reward fijo
                # NOTA: el f16 introduce error de redondeo aquí
                r = 0.5
                new_omega = []
                for i in range(len(visited.omega)):
                    val = (1 - beta) * visited.omega[i] + beta * r
                    # f16 quantization
                    new_omega.append(round(val, 4))
                # Normalizar (simulando f16: normalize con error)
                norm = math.sqrt(sum(x*x for x in new_omega))
                if norm > 0:
                    visited.omega = [round(x / norm, 4) for x in new_omega]
                else:
                    visited.omega = new_omega
                
                # 3. Update φ (Ec.3): Kuramoto → u16
                delta = 0.1 * r * (0 - visited.phase)
                new_phase = (visited.phase + delta) % 6.2832
                visited.phase = new_phase  # usa el setter u16
                
                # 4. Update V (Ec.5): decaimiento exponencial → u16
                A = 1.0
                decay = math.exp(-gamma)
                new_v = visited.vitality * decay + A * (1 - decay)
                visited.vitality = new_v  # usa el setter u16

        # 5. Poda (vitalidad < θ_death)
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
        return snapshot, pruned

    def run(self, n_ticks):
        """Corre N ticks. Misma lógica que SGMEngine.run pero con NodeCore."""
        snapshots = []
        for i in range(n_ticks):
            snap, pruned = self.step()
            if i % 100 == 0:
                snapshots.append({
                    "tick": self.tick,
                    "nodes": {nid: {"omega": s["omega"], "phase": s["phase"],
                                   "vitality": s["vitality"]} for nid, s in snap.items()},
                    "pruned": pruned,
                    "threads": [{"current_node": t["current_node"], "id": t["id"]}
                               for t in self.threads],
                })
        return snapshots


# ─── Test T-INF-06: Equivalencia ───

def t_inf_06(sgm_snapshots, nodecore_snapshots, tolerance=TOLERANCE):
    """
    T-INF-06: NodeCore+EdgeTable equivalente a SGMNode dentro de tolerance.
    
    Criterios:
    a) Vitalidad |V_sgm - V_nc| < tolerance
    b) Fase |φ_sgm - φ_nc| < 1.0 rad
    c) Omega cos(ω_sgm, ω_nc) > (1 - tolerance)
    d) Pods idénticos (95%)
    e) Ruteo threads (80%)
    """
    baseline_only = nodecore_snapshots is None
    result = {
        "experiment_id": EXPERIMENT_ID,
        "test": "T-INF-06",
        "baseline_only": baseline_only,
        "config": CONFIG,
        "date": datetime.now().isoformat(),
        "pass": True,
    }

    if baseline_only:
        result["checks"] = {
            "baseline_sgm": {
                "n_snapshots": len(sgm_snapshots),
                "n_nodes_initial": len(sgm_snapshots[0]["nodes"]) if sgm_snapshots else 0,
                "n_nodes_final": len(sgm_snapshots[-1]["nodes"]) if sgm_snapshots else 0,
                "n_pruned_total": sum(len(s["pruned"]) for s in sgm_snapshots),
            }
        }
        print(f"[T-INF-06 BASELINE] SGMNode: {len(sgm_snapshots)} snapshots.")
        print(f"  Nodos iniciales: {result['checks']['baseline_sgm']['n_nodes_initial']}")
        print(f"  Nodos finales:   {result['checks']['baseline_sgm']['n_nodes_final']}")
        print(f"  Total pods:      {result['checks']['baseline_sgm']['n_pruned_total']}")
        return result

    # Comparación activa
    min_len = min(len(sgm_snapshots), len(nodecore_snapshots))
    checks = {"vitality_delta": [], "phase_delta": [], "omega_cos": [],
              "prune_match": [], "routing_match": []}

    for i in range(min_len):
        sgm_snap = sgm_snapshots[i]
        nc_snap = nodecore_snapshots[i]

        for nid in sgm_snap["nodes"]:
            if nid in nc_snap["nodes"]:
                # a) Vitalidad
                v_diff = abs(sgm_snap["nodes"][nid]["vitality"] -
                             nc_snap["nodes"][nid]["vitality"])
                checks["vitality_delta"].append(v_diff)

                # b) Fase
                phi_sgm = sgm_snap["nodes"][nid]["phase"]
                phi_nc = nc_snap["nodes"][nid]["phase"]
                phi_diff = abs(phi_sgm - phi_nc)
                phi_diff = min(phi_diff, 6.2832 - phi_diff)
                checks["phase_delta"].append(phi_diff)

                # c) Omega coseno
                cos_val = cosine(sgm_snap["nodes"][nid]["omega"],
                                 nc_snap["nodes"][nid]["omega"])
                checks["omega_cos"].append(cos_val)

        # d) Pods
        sgm_pruned = set(sgm_snap["pruned"])
        nc_pruned = set(nc_snap["pruned"])
        checks["prune_match"].append(sgm_pruned == nc_pruned)

        # e) Ruteo
        match = sum(1 for st, nt in zip(sgm_snap["threads"], nc_snap["threads"])
                    if st["current_node"] == nt["current_node"])
        total = len(sgm_snap["threads"])
        checks["routing_match"].append(match / total if total > 0 else 0)

    result["checks"] = {
        "vitality": {"mean_delta": round(sum(checks["vitality_delta"])/max(len(checks["vitality_delta"]),1), 4),
                     "max_delta": round(max(checks["vitality_delta"]) if checks["vitality_delta"] else 0, 4),
                     "threshold": tolerance, "pass": max(checks["vitality_delta"]) < tolerance if checks["vitality_delta"] else True},
        "phase": {"mean_delta": round(sum(checks["phase_delta"])/max(len(checks["phase_delta"]),1), 4),
                  "max_delta": round(max(checks["phase_delta"]) if checks["phase_delta"] else 0, 4),
                  "threshold_rad": 1.0, "pass": max(checks["phase_delta"]) < 1.0 if checks["phase_delta"] else True},
        "omega_cos": {"min_cos": round(min(checks["omega_cos"]) if checks["omega_cos"] else 1.0, 4),
                      "mean_cos": round(sum(checks["omega_cos"])/max(len(checks["omega_cos"]),1), 4),
                      "threshold": 1 - tolerance, "pass": min(checks["omega_cos"]) > (1 - tolerance) if checks["omega_cos"] else True},
        "prune_consistency": {"pass_rate": round(sum(checks["prune_match"])/len(checks["prune_match"]) if checks["prune_match"] else 1.0, 4),
                              "threshold": 0.95, "pass": sum(checks["prune_match"])/len(checks["prune_match"]) >= 0.95 if checks["prune_match"] else True},
        "routing_consistency": {"mean_match": round(sum(checks["routing_match"])/max(len(checks["routing_match"]),1), 4),
                                "threshold": 0.80, "pass": sum(checks["routing_match"])/len(checks["routing_match"]) >= 0.80 if checks["routing_match"] else True},
    }

    result["pass"] = all(v.get("pass", False) for v in result["checks"].values())

    print(f"\n[T-INF-06 EQUIVALENCIA] Resultado: {'PASS ✅' if result['pass'] else 'FAIL ❌'}")
    for name, check in result["checks"].items():
        status = "✅" if check.get("pass", False) else "❌"
        print(f"  {status} {name}: {check}")
    return result


# ─── Main ───

if __name__ == "__main__":
    print(f"T-INF-06: Equivalencia SGMNode vs NodeCore — {EXPERIMENT_ID}")
    print(f"Config: D={CONFIG['D']}, K={CONFIG['K']}, seed={CONFIG['seed']}, "
          f"passes={CONFIG['passes']}, tolerance={TOLERANCE}\n")

    # 1. Verificar si hay snapshots de baseline
    baseline_file = os.path.join("phases", "phase0_substrato",
                                 f"baseline_snapshots_{EXPERIMENT_ID}.json")
    
    if os.path.exists(baseline_file):
        print(f"[INFO] Cargando baseline desde {baseline_file}")
        with open(baseline_file) as f:
            sgm_snapshots = json.load(f)
        print(f"[INFO] Baseline: {len(sgm_snapshots)} snapshots, "
              f"{len(sgm_snapshots[0]['nodes'])} nodos iniciales")
    else:
        print(f"[WARN] No se encontró baseline. Corriendo SGMNode como baseline...")
        engine = SGMEngine(CONFIG)
        engine.build_corpus_graph(n_nodes=50, n_edges=100)
        sgm_snapshots = engine.run(CONFIG["passes"])
        # Guardar baseline
        os.makedirs("phases/phase0_substrato", exist_ok=True)
        with open(baseline_file, "w") as f:
            json.dump(sgm_snapshots, f, indent=2)
        print(f"[INFO] Baseline grabado en {baseline_file}: {len(sgm_snapshots)} snapshots")

    # 2. Correr NodeCore con MISMA seed/config
    print(f"\n[INFO] Corriendo NodeCore con mismo seed/config...")
    nc_engine = NodeCoreEngine(CONFIG)
    nc_engine.build_corpus_graph(n_nodes=50, n_edges=100)
    nc_snapshots = nc_engine.run(CONFIG["passes"])
    print(f"[INFO] NodeCore: {len(nc_snapshots)} snapshots, "
          f"{len(nc_snapshots[0]['nodes'])} nodos iniciales")

    # 3. Run test de equivalencia
    result = t_inf_06(sgm_snapshots=sgm_snapshots,
                      nodecore_snapshots=nc_snapshots,
                      tolerance=TOLERANCE)

    # 4. Guardar resultados
    results_file = os.path.join("phases", "phase0_substrato",
                               f"results_{EXPERIMENT_ID}.json")
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n[INFO] Resultados guardados en: {results_file}")
