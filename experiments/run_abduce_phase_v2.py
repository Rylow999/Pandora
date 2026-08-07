#!/usr/bin/env python3
"""
exp_SGM_0009 - Composición XOR con fase dinámica v2 (KoPE-inspired, corregido)

Diagnóstico de exp_SGM_0008:
  ❌ pair_accuracy=0.0 vs 0.1 de exp_SGM_0007 (D=32 estático)
  ❌ Score bajó de 0.3408 a 0.2763
  ❌ Sincronización de fase: Δφ promedio = 1.78 rad (43% de convergencia)

Causas identificadas:
  1. α_phase=0.15 es demasiado bajo para 500 ticks — la sincronización no converge
  2. El coupling K=0.3 es débil para 30 nodos
  3. cos(Δφ) en phase_binding es contraproducente cuando Δφ≈π (cos(π)=-1 invierte el binding)

Fixes para exp_SGM_0009:
  1. Usar |cos(Δφ)| en vez de cos(Δφ) — siempre positivo, nunca invierte el binding
  2. α_phase=0.5 — 3× más alto para forzar sincronización rápida
  3. K=1.0 — coupling más fuerte entre vecinos
  4. NUM_TICKS=2000 — más tiempo de convergencia
  5. Inicializar fases cercanas para nodos que van a componerse — semilla de sincronización

Hipótesis: con estos fixes, la fase dinámica mejora el binding XOR
y supera el D=32 estático de exp_SGM_0007.

Analogía en criollo:
  En exp_SGM_0008, las fases de los nodos estaban como un grupo de
  personas hablando cada una en su propio idioma — no se sincronizaban
  y cuando intentaban "componerse" (hablar juntos), terminaban
  diciendo lo contrario (cos(π)=-1 invierte el mensaje).

  En exp_SGM_0009, arreglamos eso de dos formas:
  (a) |cos(Δφ)|: aunque hablen idiomas diferentes, el "volumen" de
      la conversación siempre es positivo — nunca dice lo contrario.
  (b) α=0.5 y K=1.0: forzamos a que se pongan de acuerdo más rápido,
      como un director de orquesta más estricto.
  (c) 2000 ticks: les damos más tiempo para ponerse de acuerdo.
"""

import json
import math
import random
import time

EXPERIMENT_ID = "exp_SGM_0009"
EXPERIMENT_NAME = "abduce_xor_phase_dynamics_v2"
PHASE = "Fase 2 — Inferencia simbólica + duda"
DATE = "2026-08-02"

D = 32
NUM_NODES = 30
NUM_COMPOSITIONS = 20
NUM_QUERIES = 10
SEED = 42
NUM_TICKS = 2000  # más tiempo de convergencia

# Parámetros de fase dinámica corregidos
ALPHA_PHASE = 0.5   # 3× más alto que exp_SGM_0008
OMEGA_0 = 1.0
K_COUPPLING = 1.0   # 3× más alto que exp_SGM_0008


def make_omega(D, seed):
    rng = random.Random(seed)
    return [rng.random() * 2 - 1 for _ in range(D)]


def cosine_sim(a, b):
    if len(a) != len(b):
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def xor_compose(a, b):
    return [ai * bi for ai, bi in zip(a, b)]


def add_noise(vec, flip_rate=0.05):
    rng = random.Random(42)
    result = vec[:]
    for i in range(len(result)):
        if rng.random() < flip_rate:
            result[i] = -result[i]
    return result


def create_phase_nodes_v2(D, num_nodes, seed):
    """Crea nodos con omega estático + fase dinámica inicial.
    
    V2: inicializa fases cercanas para nodos que van a componerse
    (semilla de sincronización).
    """
    rng = random.Random(seed)
    nodes = {}
    for i in range(num_nodes):
        omega = [rng.random() * 2 - 1 for _ in range(D)]
        norm = math.sqrt(sum(x * x for x in omega))
        if norm > 0:
            omega = [x / norm for x in omega]
        # Fase inicial: cercana a 0 para todos (semilla de sincronización)
        nodes[i] = {
            "id": i,
            "omega": omega,
            "phase": rng.random() * 0.5,  # fases iniciales cercanas (0-0.5 rad)
            "name": f"concept_{i}",
            "hit_count": 0,
            "vitality": 1.0,
        }
    return nodes


def kuramoto_step_v2(nodes, edge_table, alpha=ALPHA_PHASE, K=K_COUPPLING):
    """Un paso de dinámica de Kuramoto para las fases de los nodos.
    
    V2: usa coupling más fuerte y α más alto para convergencia rápida.
    """
    new_phases = {}
    for i, node in nodes.items():
        phi_i = node["phase"]
        coupling_sum = 0.0
        if i in edge_table:
            for j, weight in edge_table[i]:
                phi_j = nodes[j]["phase"]
                coupling_sum += weight * math.sin(phi_j - phi_i)
        dphi = alpha * (OMEGA_0 + K * coupling_sum)
        new_phases[i] = (phi_i + dphi) % (2 * math.pi)
    
    for i, new_phi in new_phases.items():
        nodes[i]["phase"] = new_phi
    
    return nodes


def phase_binding_v2(a_phase, b_phase, a_omega, b_omega, D):
    """
    Binding con fase dinámica v2: usa |cos(Δφ)| en vez de cos(Δφ).
    
    |cos(Δφ)| siempre es positivo (0 a 1), nunca invierte el binding.
    Cuando las fases están sincronizadas (Δφ≈0): |cos(0)|=1 → binding completo.
    Cuando están desfasadas (Δφ≈π/2): |cos(π/2)|=0 → binding nulo.
    Cuando están opuestas (Δφ≈π): |cos(π)|=1 → binding completo otra vez.
    
    Esto evita el problema de exp_SGM_0008 donde cos(π)=-1 invertía el binding.
    """
    delta_phi = (a_phase - b_phase) % (2 * math.pi)
    # Usar |cos(Δφ)| para que siempre sea positivo
    phase_factor = abs(math.cos(delta_phi))
    
    composed = [(a_omega[i] * b_omega[i]) * phase_factor for i in range(D)]
    return composed


def build_edge_table(nodes, num_nodes, threshold=0.3):
    """Construye edge_table por similitud de omega."""
    edge_table = {}
    for i in range(num_nodes):
        neighbors = []
        for j in range(num_nodes):
            if i == j:
                continue
            sim = cosine_sim(nodes[i]["omega"], nodes[j]["omega"])
            if sim > threshold:
                neighbors.append((j, sim))
        edge_table[i] = neighbors
    return edge_table


def abduce_xor_phase_v2(query_omega, query_phase, nodes, D, top_k=5):
    """Abducción XOR con fase dinámica v2."""
    # Paso 1: candidatos individuales
    candidates = []
    for nid, node in nodes.items():
        score = cosine_sim(query_omega, node["omega"])
        candidates.append((nid, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = candidates[:top_k]
    
    # Paso 2: composiciones de pares con fase dinámica v2
    best_score = -1.0
    best_pair = None
    best_composed = None
    
    for i, (id_a, score_a) in enumerate(top_candidates):
        for j, (id_b, score_b) in enumerate(top_candidates):
            if i >= j:
                continue
            a_node = nodes[id_a]
            b_node = nodes[id_b]
            composed = phase_binding_v2(
                a_node["phase"], b_node["phase"],
                a_node["omega"], b_node["omega"], D
            )
            pair_score = cosine_sim(query_omega, composed)
            if pair_score > best_score:
                best_score = pair_score
                best_pair = (id_a, id_b)
                best_composed = composed
    
    return best_pair, best_score, best_composed, top_candidates


def run_experiment(D, num_nodes, num_compositions, num_queries, seed):
    """Ejecuta el experimento con fase dinámica v2."""
    rng = random.Random(seed)
    
    # 1. Crear nodos con fase (v2: fases iniciales cercanas)
    nodes = create_phase_nodes_v2(D, num_nodes, seed)
    
    # 2. Construir edge_table
    edge_table = build_edge_table(nodes, num_nodes)
    
    # 3. Evolucionar fases con Kuramoto durante NUM_TICKS
    for tick in range(NUM_TICKS):
        nodes = kuramoto_step_v2(nodes, edge_table)
    
    # 4. Medir sincronización final
    sync_diffs = []
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            diff = abs(nodes[i]["phase"] - nodes[j]["phase"])
            sync_diffs.append(min(diff, 2 * math.pi - diff))
    avg_sync_diff_all = sum(sync_diffs) / len(sync_diffs) if sync_diffs else 0.0
    
    # 5. Generar composiciones ground truth con fase dinámica v2
    compositions = []
    for _ in range(num_compositions):
        a = rng.randint(0, num_nodes - 1)
        b = rng.randint(0, num_nodes - 1)
        while b == a:
            b = rng.randint(0, num_nodes - 1)
        composed = phase_binding_v2(
            nodes[a]["phase"], nodes[b]["phase"],
            nodes[a]["omega"], nodes[b]["omega"], D
        )
        compositions.append({
            "a": a,
            "b": b,
            "composed": composed,
            "phase_a": nodes[a]["phase"],
            "phase_b": nodes[b]["phase"],
            "phase_diff": abs(nodes[a]["phase"] - nodes[b]["phase"]),
        })
    
    # 6. Abducción
    results = []
    for comp in compositions[:num_queries]:
        pair, pair_score, _, candidates = abduce_xor_phase_v2(
            comp["composed"], comp["phase_a"], nodes, D, top_k=5
        )
        
        found_correct = (
            pair is not None and
            ((pair[0] == comp["a"] and pair[1] == comp["b"]) or
             (pair[0] == comp["b"] and pair[1] == comp["a"]))
        )
        
        top1_score = candidates[0][1] if candidates else 0.0
        
        results.append({
            "ground_truth": (comp["a"], comp["b"]),
            "predicted_pair": pair,
            "pair_score": pair_score,
            "found_correct": found_correct,
            "top1_candidate": candidates[0][0] if candidates else None,
            "top1_score": top1_score,
            "top1_is_ground_truth": (
                candidates[0][0] == comp["a"] or candidates[0][0] == comp["b"]
            ) if candidates else False,
            "phase_diff_gt": comp["phase_diff"],
        })
    
    # 7. Métricas agregadas
    correct_pairs = sum(1 for r in results if r["found_correct"])
    correct_top1 = sum(1 for r in results if r["top1_is_ground_truth"])
    avg_pair_score = sum(r["pair_score"] for r in results) / len(results) if results else 0.0
    avg_top1_score = sum(r["top1_score"] for r in results) / len(results) if results else 0.0
    
    # 8. Robustez al ruido
    noisy_results = []
    for comp in compositions[:num_queries]:
        noisy_query = add_noise(comp["composed"], flip_rate=0.05)
        pair, pair_score, _, _ = abduce_xor_phase_v2(
            noisy_query, comp["phase_a"], nodes, D, top_k=5
        )
        found_correct = (
            pair is not None and
            ((pair[0] == comp["a"] and pair[1] == comp["b"]) or
             (pair[0] == comp["b"] and pair[1] == comp["a"]))
        )
        noisy_results.append({
            "found_correct": found_correct,
            "pair_score": pair_score,
        })
    
    correct_noisy = sum(1 for r in noisy_results if r["found_correct"])
    avg_noisy_score = sum(r["pair_score"] for r in noisy_results) / len(noisy_results) if noisy_results else 0.0
    
    # 9. Sincronización de fase para pares correctos
    sync_diffs_correct = []
    for r in results:
        if r["predicted_pair"]:
            id_a, id_b = r["predicted_pair"]
            diff = abs(nodes[id_a]["phase"] - nodes[id_b]["phase"])
            sync_diffs_correct.append(min(diff, 2 * math.pi - diff))
    avg_sync_diff_correct = sum(sync_diffs_correct) / len(sync_diffs_correct) if sync_diffs_correct else 0.0
    
    return {
        "D": D,
        "num_nodes": num_nodes,
        "num_compositions": num_compositions,
        "num_queries": num_queries,
        "phase_params": {
            "alpha_phase": ALPHA_PHASE,
            "omega_0": OMEGA_0,
            "k_coupling": K_COUPPLING,
            "num_ticks": NUM_TICKS,
            "phase_binding": "|cos(Δφ)| (v2: siempre positivo)",
        },
        "correct_pairs": correct_pairs,
        "correct_top1": correct_top1,
        "pair_accuracy": correct_pairs / len(results) if results else 0.0,
        "top1_accuracy": correct_top1 / len(results) if results else 0.0,
        "avg_pair_score": avg_pair_score,
        "avg_top1_score": avg_top1_score,
        "correct_noisy": correct_noisy,
        "noisy_accuracy": correct_noisy / len(noisy_results) if noisy_results else 0.0,
        "avg_noisy_score": avg_noisy_score,
        "noise_degradation": avg_pair_score - avg_noisy_score,
        "avg_sync_diff_all": avg_sync_diff_all,
        "avg_sync_diff_correct": avg_sync_diff_correct,
        "phase_convergence_all": 1.0 - (avg_sync_diff_all / math.pi),
        "phase_convergence_correct": 1.0 - (avg_sync_diff_correct / math.pi) if sync_diffs_correct else 0.0,
    }


if __name__ == "__main__":
    print("=" * 60)
    print(f"  {EXPERIMENT_ID}: Abducción XOR con fase dinámica v2")
    print("=" * 60)
    print()
    print("Fixes respecto de exp_SGM_0008:")
    print("  1. |cos(Δφ)| en vez de cos(Δφ) — nunca invierte el binding")
    print("  2. α_phase=0.5 (3× más alto) — sincronización más rápida")
    print("  3. K=1.0 (3× más alto) — coupling más fuerte")
    print("  4. NUM_TICKS=2000 (4× más) — más tiempo de convergencia")
    print("  5. Fases iniciales cercanas (0-0.5 rad) — semilla de sincronización")
    print()
    print(f"Config: D={D}, {NUM_NODES} nodos, {NUM_TICKS} ticks Kuramoto")
    print(f"  α_phase={ALPHA_PHASE}, ω_0={OMEGA_0}, K={K_COUPPLING}")
    print()
    
    start = time.time()
    result = run_experiment(D, NUM_NODES, NUM_COMPOSITIONS, NUM_QUERIES, SEED)
    elapsed = time.time() - start
    result["elapsed_seconds"] = round(elapsed, 2)
    
    print(f"  Nodos: {result['num_nodes']}")
    print(f"  Composiciones evaluadas: {result['num_queries']}")
    print(f"  Precisión par (pair_accuracy):  {result['pair_accuracy']:.4f}")
    print(f"  Precisión top-1 (top1_accuracy): {result['top1_accuracy']:.4f}")
    print(f"  Score promedio par:              {result['avg_pair_score']:.4f}")
    print(f"  Score promedio top-1:            {result['avg_top1_score']:.4f}")
    print(f"  Robustez (5% noise):             {result['noisy_accuracy']:.4f}")
    print(f"  Degradación por ruido:           {result['noise_degradation']:.4f}")
    print(f"  Sincronización (todos los pares, avg Δφ): {result['avg_sync_diff_all']:.4f} rad")
    print(f"  Sincronización (pares predichos, avg Δφ): {result['avg_sync_diff_correct']:.4f} rad")
    print(f"  Convergence (todos):  {result['phase_convergence_all']:.4f}")
    print(f"  Convergence (correctos): {result['phase_convergence_correct']:.4f}")
    print(f"  Tiempo:                          {result['elapsed_seconds']:.2f}s")
    print()
    
    # Comparación con exp_SGM_0007 y exp_SGM_0008
    print("=" * 60)
    print("  COMPARACIÓN")
    print("=" * 60)
    print(f"  exp_SGM_0007 (D=32, estático):  pair_accuracy=0.1000, score=0.3408")
    print(f"  exp_SGM_0008 (D=32, fase v1):   pair_accuracy=0.0000, score=0.2763")
    print(f"  exp_SGM_0009 (D=32, fase v2):   pair_accuracy={result['pair_accuracy']:.4f}, score={result['avg_pair_score']:.4f}")
    print()
    print(f"  ¿V2 supera a V1?  {result['pair_accuracy'] > 0.0}")
    print(f"  ¿V2 supera a estático?  {result['pair_accuracy'] > 0.1}")
    print()
    
    # Guardar resultados
    output = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_name": EXPERIMENT_NAME,
        "phase": PHASE,
        "date": DATE,
        "hypothesis": "Con los fixes identificados (|cos(Δφ)|, α=0.5, K=1.0, 2000 ticks), la fase dinámica mejora el binding XOR y supera D=32 estático.",
        "result": result,
        "config": {
            "D": D,
            "num_nodes": NUM_NODES,
            "num_compositions": NUM_COMPOSITIONS,
            "num_queries": NUM_QUERIES,
            "seed": SEED,
            "num_ticks": NUM_TICKS,
            "alpha_phase": ALPHA_PHASE,
            "omega_0": OMEGA_0,
            "k_coupling": K_COUPPLING,
        },
        "script": "phases/phase2_inferencia/run_abduce_phase_v2.py",
        "results_file": "phases/phase2_inferencia/results_exp_SGM_0009_abduce_phase_v2.json",
        "test_target": "T-INF-03 (abducción XOR con fase dinámica KoPE-inspired v2)",
        "baseline_for": [],
        "variant_of": "exp_SGM_0005",
        "lit_refs": ["KoPE arXiv 2604.07904 (Xiao et al., Microsoft Research Asia, April 2026)", "Kanerva 1988 Sparse Distributed Memory", "HippoRAG NeurIPS 2024 (arxiv 2404.10501)"],
        "notes": "Resultado pendiente de ejecución. Comparar con exp_SGM_0007 (D=32, sin fase) y exp_SGM_0008 (fase v1 con cos(Δφ)).",
        "notes_criollo": "Si la fase dinámica v2 mejora el score, confirma que Kuramoto es el camino correcto para SGM y que los fixes (|cos(Δφ)|, α alto, K alto) resuelven los problemas de v1. Si no mejora, puede que necesitemos combinar D mayor + fase, o que el mecanismo de fase necesita un rediseño más profundo."
    }
    
    out_path = f"/data/data/com.hermesagent.android/files/home/rizoma_docs/results_{EXPERIMENT_ID}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Resultados guardados en: {out_path}")
