#!/usr/bin/env python3
"""
exp_SGM_0011 - Composición XOR con D=128 (Kanerva recomienda D≥64
para vectores continuos, D=128 para margen de seguridad)

Motivación:
  La serie de experimentos de fase dinámica (exp_SGM_0008-0010)
  demostró que:
  1. La fase dinámica como multiplicador del binding NO funciona
     (pair_accuracy=0.0 en todos los casos)
  2. La fase como sesgo relacional re-pondera pero no compensa
     el ruido del binding a D=32
  3. KoPE funciona en ARC-AGI con D=512+ donde la señal del
     binding es mucho más fuerte

  Hipótesis de exp_SGM_0011:
  El cuello de botella es D=32 (demasiado ruidoso para binding
  XOR por producto element-wise). Aumentar a D=128 debería
  reducir el ruido y mejorar pair_accuracy.

  Esto es consistente con la recomendación de Kanerva (SDM):
  D≥64 para vectores continuos, y con la evidencia de exp_SGM_0007
  donde D=32 ya era mejor que D=16 pero D=64 no añadió beneficio.
  La diferencia es que D=64 en exp_SGM_0007 usaba el mismo setup
  que D=32 (sin fase). Aquí probamos D=128 con el mecanismo de
  fase como sesgo relacional (v3 de exp_SGM_0010) para ver si
  la combinación D alto + fase como sesgo supera a D=32 estático.

  Analogía en criollo:
  Imaginate que buscás a dos personas en una ciudad. Con D=32,
  la ciudad es chica — hay mucha superposición entre las
  descripciones de diferentes personas (ruido). Con D=128,
  la ciudad es más grande — cada persona tiene más espacio
  para tener una descripción única, y es más fácil distinguir
  al par correcto de los distractores.

  La fase dinámica (sesgo relacional) es como tener un mapa
  que te dice "esas dos personas suelen estar en el mismo
  lugar" — te ayuda a priorizar, pero no reemplaza la
  necesidad de que las descripciones sean distintas.

Métricas:
  - pair_accuracy (¿encuentra el par correcto?)
  - avg_pair_score (similitud del par predicho vs ground truth)
  - noisy_accuracy (robustez con 5% de ruido)
  - Comparación directa con exp_SGM_0007 (D=32, estático)
"""

import json
import math
import random
import time

EXPERIMENT_ID = "exp_SGM_0011"
EXPERIMENT_NAME = "abduce_xor_D128"
PHASE = "Fase 2 — Inferencia simbólica + duda"
DATE = "2026-08-02"

D = 128  # 4× D=32 de exp_SGM_0007
NUM_NODES = 30
NUM_COMPOSITIONS = 20
NUM_QUERIES = 10
SEED = 42
NUM_TICKS = 500

# Parámetros de fase dinámica (sesgo relacional, v3)
ALPHA_PHASE = 0.5
OMEGA_0 = 1.0
K_COUPPLING = 1.0
LAMBDA_PHASE = 0.5
SIGMA_PHASE = math.pi / 4


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


def create_phase_nodes(D, num_nodes, seed):
    """Crea nodos con omega estático + fase dinámica inicial."""
    rng = random.Random(seed)
    nodes = {}
    for i in range(num_nodes):
        omega = [rng.random() * 2 - 1 for _ in range(D)]
        norm = math.sqrt(sum(x * x for x in omega))
        if norm > 0:
            omega = [x / norm for x in omega]
        nodes[i] = {
            "id": i,
            "omega": omega,
            "phase": rng.random() * 0.5,
            "name": f"concept_{i}",
            "hit_count": 0,
            "vitality": 1.0,
        }
    return nodes


def kuramoto_step(nodes, edge_table, alpha=ALPHA_PHASE, K=K_COUPPLING):
    """Un paso de dinámica de Kuramoto para las fases de los nodos."""
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


def phase_bias(delta_phi, lambda_param=LAMBDA_PHASE, sigma=SIGMA_PHASE):
    """Sesgo relacional de fase (gaussiano sobre Δφ)."""
    return math.exp(-(delta_phi ** 2) / (2 * sigma ** 2))


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


def abduce_xor_phase_bias(query_omega, query_phase, nodes, D, top_k=5):
    """
    Abducción XOR con sesgo relacional de fase (KoPE v3).
    El binding NO se modula por la fase. La fase es un sesgo
    que re-pondera el score de búsqueda.
    """
    # Paso 1: candidatos individuales por similitud de omega
    candidates = []
    for nid, node in nodes.items():
        score = cosine_sim(query_omega, node["omega"])
        candidates.append((nid, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = candidates[:top_k]
    
    # Paso 2: composiciones de pares con binding SIN modulación de fase
    # y score re-ponderado por sesgo de fase
    best_score = -1.0
    best_pair = None
    best_composed = None
    best_binding_score = 0.0
    best_phase_affinity = 0.0
    
    for i, (id_a, score_a) in enumerate(top_candidates):
        for j, (id_b, score_b) in enumerate(top_candidates):
            if i >= j:
                continue
            a_node = nodes[id_a]
            b_node = nodes[id_b]
            
            # Binding SIN modulación de fase
            composed = xor_compose(a_node["omega"], b_node["omega"])
            binding_score = cosine_sim(query_omega, composed)
            
            # Sesgo de fase (gaussiano sobre Δφ)
            delta_phi = abs(a_node["phase"] - b_node["phase"])
            delta_phi = min(delta_phi, 2 * math.pi - delta_phi)
            p_bias = phase_bias(delta_phi)
            
            # Score final: binding re-ponderado por sesgo de fase
            final_score = binding_score * (1 + LAMBDA_PHASE * p_bias)
            
            if final_score > best_score:
                best_score = final_score
                best_pair = (id_a, id_b)
                best_composed = composed
                best_binding_score = binding_score
                best_phase_affinity = p_bias
    
    return best_pair, best_score, best_composed, best_binding_score, best_phase_affinity, top_candidates


def run_experiment(D, num_nodes, num_compositions, num_queries, seed):
    """Ejecuta el experimento con D=128 y sesgo relacional de fase."""
    rng = random.Random(seed)
    
    # 1. Crear nodos con fase
    nodes = create_phase_nodes(D, num_nodes, seed)
    
    # 2. Construir edge_table
    edge_table = build_edge_table(nodes, num_nodes)
    
    # 3. Evolucionar fases con Kuramoto durante NUM_TICKS
    for tick in range(NUM_TICKS):
        nodes = kuramoto_step(nodes, edge_table)
    
    # 4. Medir sincronización final
    sync_diffs_all = []
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            diff = abs(nodes[i]["phase"] - nodes[j]["phase"])
            sync_diffs_all.append(min(diff, 2 * math.pi - diff))
    avg_sync_diff_all = sum(sync_diffs_all) / len(sync_diffs_all) if sync_diffs_all else 0.0
    
    # 5. Generar composiciones ground truth (binding puro, sin fase)
    compositions = []
    for _ in range(num_compositions):
        a = rng.randint(0, num_nodes - 1)
        b = rng.randint(0, num_nodes - 1)
        while b == a:
            b = rng.randint(0, num_nodes - 1)
        composed = xor_compose(nodes[a]["omega"], nodes[b]["omega"])
        compositions.append({
            "a": a,
            "b": b,
            "composed": composed,
            "phase_a": nodes[a]["phase"],
            "phase_b": nodes[b]["phase"],
            "phase_diff": abs(nodes[a]["phase"] - nodes[b]["phase"]),
        })
    
    # 6. Abducción con sesgo de fase
    results = []
    for comp in compositions[:num_queries]:
        pair, final_score, _, binding_score, p_bias, candidates = abduce_xor_phase_bias(
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
            "final_score": final_score,
            "binding_score": binding_score,
            "phase_affinity": p_bias,
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
    avg_final_score = sum(r["final_score"] for r in results) / len(results) if results else 0.0
    avg_binding_score = sum(r["binding_score"] for r in results) / len(results) if results else 0.0
    avg_phase_affinity = sum(r["phase_affinity"] for r in results) / len(results) if results else 0.0
    avg_top1_score = sum(r["top1_score"] for r in results) / len(results) if results else 0.0
    
    # 8. Robustez al ruido
    noisy_results = []
    for comp in compositions[:num_queries]:
        noisy_query = add_noise(comp["composed"], flip_rate=0.05)
        pair, final_score, _, binding_score, p_bias, _ = abduce_xor_phase_bias(
            noisy_query, comp["phase_a"], nodes, D, top_k=5
        )
        found_correct = (
            pair is not None and
            ((pair[0] == comp["a"] and pair[1] == comp["b"]) or
             (pair[0] == comp["b"] and pair[1] == comp["a"]))
        )
        noisy_results.append({
            "found_correct": found_correct,
            "final_score": final_score,
            "binding_score": binding_score,
            "phase_affinity": p_bias,
        })
    
    correct_noisy = sum(1 for r in noisy_results if r["found_correct"])
    avg_noisy_score = sum(r["final_score"] for r in noisy_results) / len(noisy_results) if noisy_results else 0.0
    
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
        },
        "bias_params": {
            "lambda_phase": LAMBDA_PHASE,
            "sigma_phase": SIGMA_PHASE,
            "phase_binding": "sesgo relacional (no multiplicador)",
        },
        "correct_pairs": correct_pairs,
        "correct_top1": correct_top1,
        "pair_accuracy": correct_pairs / len(results) if results else 0.0,
        "top1_accuracy": correct_top1 / len(results) if results else 0.0,
        "avg_final_score": avg_final_score,
        "avg_binding_score": avg_binding_score,
        "avg_phase_affinity": avg_phase_affinity,
        "avg_top1_score": avg_top1_score,
        "correct_noisy": correct_noisy,
        "noisy_accuracy": correct_noisy / len(noisy_results) if noisy_results else 0.0,
        "avg_noisy_score": avg_noisy_score,
        "noise_degradation": avg_final_score - avg_noisy_score,
        "avg_sync_diff_all": avg_sync_diff_all,
        "avg_sync_diff_correct": avg_sync_diff_correct,
        "phase_convergence_all": 1.0 - (avg_sync_diff_all / math.pi),
        "phase_convergence_correct": 1.0 - (avg_sync_diff_correct / math.pi) if sync_diffs_correct else 0.0,
    }


if __name__ == "__main__":
    print("=" * 60)
    print(f"  {EXPERIMENT_ID}: Abducción XOR con D=128")
    print("=" * 60)
    print()
    print("Hipótesis: D=128 reduce el ruido del binding XOR")
    print("y mejora pair_accuracy respecto de D=32 (exp_SGM_0007).")
    print()
    print(f"Config: D={D}, {NUM_NODES} nodos, {NUM_TICKS} ticks Kuramoto")
    print(f"  α_phase={ALPHA_PHASE}, ω_0={OMEGA_0}, K={K_COUPPLING}")
    print(f"  λ_phase={LAMBDA_PHASE}, σ_phase={SIGMA_PHASE:.4f}")
    print()
    
    start = time.time()
    result = run_experiment(D, NUM_NODES, NUM_COMPOSITIONS, NUM_QUERIES, SEED)
    elapsed = time.time() - start
    result["elapsed_seconds"] = round(elapsed, 2)
    
    print(f"  Nodos: {result['num_nodes']}")
    print(f"  Composiciones evaluadas: {result['num_queries']}")
    print(f"  Precisión par (pair_accuracy):  {result['pair_accuracy']:.4f}")
    print(f"  Precisión top-1 (top1_accuracy): {result['top1_accuracy']:.4f}")
    print(f"  Score final promedio:            {result['avg_final_score']:.4f}")
    print(f"  Score binding promedio (sin fase): {result['avg_binding_score']:.4f}")
    print(f"  Affinidad de fase promedio:      {result['avg_phase_affinity']:.4f}")
    print(f"  Robustez (5% noise):             {result['noisy_accuracy']:.4f}")
    print(f"  Degradación por ruido:           {result['noise_degradation']:.4f}")
    print(f"  Sincronización (todos, avg Δφ): {result['avg_sync_diff_all']:.4f} rad")
    print(f"  Sincronización (correctos, avg Δφ): {result['avg_sync_diff_correct']:.4f} rad")
    print(f"  Convergence (todos):  {result['phase_convergence_all']:.4f}")
    print(f"  Convergence (correctos): {result['phase_convergence_correct']:.4f}")
    print(f"  Tiempo:                          {result['elapsed_seconds']:.2f}s")
    print()
    
    # Comparación con todos los experimentos previos
    print("=" * 60)
    print("  COMPARACIÓN CON TODOS LOS PRECEDENTES")
    print("=" * 60)
    print(f"  exp_SGM_0007 (D=16, estático):     pair_acc=0.0000, score=0.2503")
    print(f"  exp_SGM_0007 (D=32, estático):     pair_acc=0.1000, score=0.3408")
    print(f"  exp_SGM_0007 (D=64, estático):     pair_acc=0.1000, score=0.2802")
    print(f"  exp_SGM_0008 (D=32, fase v1):      pair_acc=0.0000, score=0.2763")
    print(f"  exp_SGM_0009 (D=32, fase v2):      pair_acc=0.0000, score=0.1780")
    print(f"  exp_SGM_0010 (D=32, fase sesgo):   pair_acc=0.0000, score=0.2654")
    print(f"  exp_SGM_0011 (D=128, fase sesgo):  pair_acc={result['pair_accuracy']:.4f}, score={result['avg_final_score']:.4f}")
    print()
    print(f"  ¿D=128 supera a D=32 estático?  {result['pair_accuracy'] > 0.1}")
    print(f"  ¿D=128 supera a D=32 con fase?  {result['pair_accuracy'] > 0.0}")
    print()
    
    # Guardar resultados
    output = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_name": EXPERIMENT_NAME,
        "phase": PHASE,
        "date": DATE,
        "hypothesis": "D=128 reduce el ruido del binding XOR lo suficiente como para superar el pair_accuracy de D=32 estático (0.1). La fase como sesgo relacional (v3) re-pondera positivamente los pares correctos pero no compensa el ruido de D=32.",
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
            "lambda_phase": LAMBDA_PHASE,
            "sigma_phase": SIGMA_PHASE,
        },
        "script": "phases/phase2_inferencia/run_abduce_xor_D128.py",
        "results_file": "phases/phase2_inferencia/results_exp_SGM_0011_abduce_xor_D128.json",
        "test_target": "T-INF-03 (abducción XOR con D=128 y sesgo relacional de fase)",
        "baseline_for": [],
        "variant_of": "exp_SGM_0007",
        "lit_refs": ["KoPE arXiv 2604.07904 (Xiao et al., Microsoft Research Asia, April 2026)", "Kanerva 1988 Sparse Distributed Memory", "HippoRAG NeurIPS 2024 (arxiv 2404.10501)"],
        "notes": "Resultado pendiente de ejecución. Comparar con exp_SGM_0007 (D=32, estático) y exp_SGM_0010 (D=32, fase sesgo).",
        "notes_criollo": "Si D=128 mejora pair_accuracy, confirma que el ruido del binding era el cuello de botella y que aumentar D es el camino correcto para SGM. Si D=128 no mejora, el problema no es la dimensionalidad sino el mecanismo de binding XOR por producto element-wise (que es inherentemente ruidoso para vectores continuos). En ese caso, necesitaríamos binding inverso (b = a⁻¹ * c) o un mecanismo completamente diferente."
    }
    
    out_path = f"/data/data/com.hermesagent.android/files/home/rizoma_docs/results_{EXPERIMENT_ID}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Resultados guardados en: {out_path}")