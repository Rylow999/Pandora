#!/usr/bin/env python3
"""
T-INF-06: Equivalencia funcional SGMNode (v1.3) vs NodeCore+EdgeTable (v1.4)

Setup: mismo grafo pequeño, representado con SGMNode y con NodeCore+EdgeTable.
Acción: correr los mismos N ticks sobre ambas representaciones.
Esperado: resultados de categoría/dolor/memoria equivalentes dentro del
margen de error introducido por la cuantización (f16, punto fijo u8/u16).

Este test se escribe ANTES de migrar a NodeCore, corre contra SGMNode (baseline),
y luego se re-corre contra NodeCore para validar T-INF-06.

Regla del protocolo SGM: este test debe pasar ANTES de que Fase 0 se considere completa.
"""

import json
import sys
import os
import random
from datetime import datetime

# ─── Configuración del experimento ───

EXPERIMENT_ID = "exp_SGM_0003_nodecore_equiv_teorica"

# Hyperparámetros según SGM v1.4 §7 (tabla de parámetros)
CONFIG = {
    "D": 16,           # dimensión vectorial (testeo en D=16, production D=384)
    "K": 10,           # cadenas paralelas
    "seed": 42,
    "epochs": 3,
    "passes": 1000,    # ticks por pass
    "corpus": "donquijote_20k_tokens_v14d",
    "beta": 0.10,      # Ec.1
    "gamma": 0.01,     # Ec.5
    "alpha": 5.0,      # Ec.2
    "theta_death": 0.10,
}

# ─── Motor de referencia: SGMNode (v1.3 / v0.14d) ───

def normalize(v):
    norm = sum(x*x for x in v) ** 0.5
    if norm == 0: return v
    return [x/norm for x in v]

def cosine(a, b):
    na, nb = normalize(a), normalize(b)
    return sum(x*y for x,y in zip(na, nb))

def dot(a, b):
    return sum(x*y for x,y in zip(a, b))

class SGMNode:
    """Representación original: Vec<f32>, floats para todo."""
    def __init__(self, node_id, omega, phase=0.0, vitality=1.0):
        self.id = node_id
        self.omega = list(omega)  # f32
        self.phase = phase        # f32
        self.vitality = vitality  # f32
        self.connections = []     # Vec<(target_id, weight, conn_type)>

    def to_dict(self):
        return {"id": self.id, "omega": self.omega, "phase": self.phase,
                "vitality": self.vitality, "connections": self.connections}

class SGMEngine:
    def __init__(self, config):
        self.config = config
        self.nodes = {}
        self.threads = []
        self.rng = random.Random(config["seed"])
        self.tick = 0

    def build_corpus_graph(self, n_nodes=50, n_edges=100):
        """Construye un grafo pequeño reproducible con seed fijo."""
        D = self.config["D"]
        for i in range(n_nodes):
            omega = normalize([self.rng.gauss(0, 1) for _ in range(D)])
            self.nodes[i] = SGMNode(i, omega, phase=self.rng.uniform(0, 6.28),
                                    vitality=self.rng.uniform(0.3, 1.0))
        for _ in range(n_edges):
            a = self.rng.randint(0, n_nodes-1)
            b = self.rng.randint(0, n_nodes-1)
            if a != b:
                w = self.rng.uniform(0.3, 1.0)
                self.nodes[a].connections.append((b, w, "Causal"))
        for k in range(self.config["K"]):
            start = self.rng.randint(0, n_nodes-1)
            self.threads.append({"id": k, "current_node": start,
                                 "trajectory": [(start, self.tick)]})

    def step(self):
        """Un tick del motor SGM completo (Ecuaciones 1-7)."""
        beta = self.config["beta"]
        gamma = self.config["gamma"]
        alpha = self.config["alpha"]
        theta_death = self.config["theta_death"]

        # Snapshot para comparación
        snapshot = {}
        for nid, node in self.nodes.items():
            snapshot[nid] = {
                "omega": list(node.omega),
                "phase": node.phase,
                "vitality": node.vitality,
            }

        # 1. Mover cadenas por afinidad (Ec.2)
        for thread in self.threads:
            curr = self.nodes[thread["current_node"]]
            affinities = []
            for target_id, weight, conn_type in curr.connections:
                target = self.nodes[target_id]
                aff = sum(x*y for x,y in zip(curr.omega, target.omega))
                boosted = aff * weight
                affinities.append((target_id, boosted))
            if affinities:
                affinities.sort(key=lambda x: x[1], reverse=True)
                top_id = affinities[0][0]
                thread["current_node"] = top_id
                thread["trajectory"].append((top_id, self.tick))
                visited = self.nodes[top_id]
                # 2. Actualizar vector (Ec.1) — TD-learning simple
                r = 0.5  # reward fijo para test determinista
                for i in range(len(visited.omega)):
                    visited.omega[i] = (1-beta)*visited.omega[i] + beta*r
                visited.omega = normalize(visited.omega)
                # 3. Actualizar fase (Ec.3 — Kuramoto simplificado)
                delta = 0.1 * r * (0 - visited.phase)  # θ_a=0 simplificado
                visited.phase = (visited.phase + delta) % 6.28
                # 4. Actualizar vitalidad (Ec.5)
                A = 1.0  # actividad
                visited.vitality = visited.vitality * (1 - 1e-10) ** gamma + A * (1 - (1 - 1e-10) ** gamma)

        # 5. Poda (Ec.5 threshold)
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
        """Corre N ticks y devuelve snapshots para comparación."""
        snapshots = []
        for i in range(n_ticks):
            snap, pruned = self.step()
            if i % 100 == 0:  # snapshot cada 100 ticks
                snapshots.append({
                    "tick": self.tick,
                    "nodes": {nid: {"omega": s["omega"], "phase": s["phase"],
                                   "vitality": s["vitality"]} for nid, s in snap.items()},
                    "pruned": pruned,
                    "threads": [{"current_node": t["current_node"], "id": t["id"]}
                               for t in self.threads],
                })
        return snapshots

# ─── Test de equivalencia ───

def t_inf_06_equiv(sgm_snapshots, nodecore_snapshots, tolerance=0.15):
    """
    T-INF-06: Verifica que NodeCore+EdgeTable produzca resultados equivalentes
    a SGMNode dentro del margen de cuantización.

    Criterios:
    a) Vitalidad: |V_sgm - V_nodecore| < tolerance para todos los nodos vivos.
    b) Fase: |φ_sgm - φ_nodecore| < 1.0 rad (margen amplio para u16 fijo).
    c) Omega: cos(ω_sgm, ω_nodecore) > (1 - tolerance) — dirección preserved.
    d) Topología: misma cantidad de pods por tick (±1).
    e) Ruteo: misma thread current_node al menos 80% de los snapshots.

    Si NodeCore NO existe todavía, corre SOLO contra SGMNode y graba el baseline.
    """
    baseline_only = nodecore_snapshots is None

    result = {
        "experiment_id": EXPERIMENT_ID,
        "test": "T-INF-06",
        "baseline_only": baseline_only,
        "config": CONFIG,
        "date": datetime.now().isoformat(),
        "checks": {},
        "pass": True,
    }

    if baseline_only:
        # Baseline: correr SGMNode y registrar snapshots
        result["checks"]["baseline_sgm"] = {
            "n_snapshots": len(sgm_snapshots),
            "n_nodes_initial": len(sgm_snapshots[0]["nodes"]) if sgm_snapshots else 0,
            "n_nodes_final": len(sgm_snapshots[-1]["nodes"]) if sgm_snapshots else 0,
            "n_pruned_total": sum(len(s["pruned"]) for s in sgm_snapshots),
        }
        print(f"[T-INF-06 BASELINE] SGMNode corrió {len(sgm_snapshots)} snapshots.")
        print(f"  Nodos iniciales: {result['checks']['baseline_sgm']['n_nodes_initial']}")
        print(f"  Nodos finales:   {result['checks']['baseline_sgm']['n_nodes_final']}")
        print(f"  Total pods:      {result['checks']['baseline_sgm']['n_pruned_total']}")
        print(f"  Snapshots grabados como baseline para NodeCore.")
        return result, sgm_snapshots

    # Comparación activa
    min_len = min(len(sgm_snapshots), len(nodecore_snapshots))
    checks = {"vitality_delta": [], "phase_delta": [], "omega_cos": [],
              "prune_match": [], "routing_match": []}

    for i in range(min_len):
        sgm_snap = sgm_snapshots[i]
        nc_snap = nodecore_snapshots[i]

        # a) Vitalidad
        for nid in sgm_snap["nodes"]:
            if nid in nc_snap["nodes"]:
                v_diff = abs(sgm_snap["nodes"][nid]["vitality"] -
                             nc_snap["nodes"][nid]["vitality"])
                checks["vitality_delta"].append(v_diff)

        # b) Fase
        for nid in sgm_snap["nodes"]:
            if nid in nc_snap["nodes"]:
                phi_sgm = sgm_snap["nodes"][nid]["phase"]
                phi_nc = nc_snap["nodes"][nid]["phase"]
                phi_diff = abs(phi_sgm - phi_nc)
                phi_diff = min(phi_diff, 6.28 - phi_diff)  # módulo 2π
                checks["phase_delta"].append(phi_diff)

        # c) Omega (coseno)
        for nid in sgm_snap["nodes"]:
            if nid in nc_snap["nodes"]:
                cos_val = cosine(sgm_snap["nodes"][nid]["omega"],
                                 nc_snap["nodes"][nid]["omega"])
                checks["omega_cos"].append(cos_val)

        # d) Pods
        sgm_pruned = set(sgm_snap["pruned"])
        nc_pruned = set(nc_snap["pruned"])
        checks["prune_match"].append(sgm_pruned == nc_pruned)

        # e) Ruteo (threads)
        match = sum(1 for st, nt in zip(sgm_snap["threads"], nc_snap["threads"])
                    if st["current_node"] == nt["current_node"])
        total = len(sgm_snap["threads"])
        checks["routing_match"].append(match / total if total > 0 else 0)

    # Aggregate results
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

    all_pass = all(v.get("pass", False) for v in result["checks"].values())
    result["pass"] = all_pass

    print(f"\n[T-INF-06 EQUIVALENCIA] Resultado: {'PASS' if all_pass else 'FAIL'}")
    for check_name, check_result in result["checks"].items():
        status = "✓" if check_result.get("pass", False) else "✗"
        print(f"  {status} {check_name}: {check_result}")

    return result, sgm_snapshots

# ─── Main ───

if __name__ == "__main__":
    print(f"T-INF-06: Equivalencia SGMNode vs NodeCore — {EXPERIMENT_ID}")
    print(f"Config: D={CONFIG['D']}, K={CONFIG['K']}, seed={CONFIG['seed']}, "
          f"passes={CONFIG['passes']}\n")

    # 1. Build baseline SGMNode
    engine = SGMEngine(CONFIG)
    engine.build_corpus_graph(n_nodes=50, n_edges=100)
    snapshots = engine.run(CONFIG["passes"])

    # 2. Run test — baseline only (NodeCore no existe todavía)
    result, baseline_snapshots = t_inf_06_equiv(sgm_snapshots=snapshots,
                                                 nodecore_snapshots=None)

    # 3. Save baseline snapshots for NodeCore comparison
    baseline_dir = "phases/phase0_substrato"
    os.makedirs(baseline_dir, exist_ok=True)

    results_file = os.path.join(baseline_dir, f"results_{EXPERIMENT_ID}.json")
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResultados guardados en: {results_file}")

    # Save baseline snapshots too
    baseline_dump = os.path.join(baseline_dir, f"baseline_snapshots_{EXPERIMENT_ID}.json")
    with open(baseline_dump, "w") as f:
        json.dump(baseline_snapshots, f, indent=2)
    print(f"Baseline snapshots guardados en: {baseline_dump}")

    print(f"\n✅ Baseline SGMNode grabado. El próximo experimento (NodeCore) debe:")
    print(f"   1. Cargar {baseline_dump}")
    print(f"   2. Correr los mismos {CONFIG['passes']} ticks")
    print(f"   3. Llamar t_inf_06_equiv() con los snapshots de NodeCore")
    print(f"   4. Verificar que todos los checks PASS")
