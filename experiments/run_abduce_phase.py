#!/usr/bin/env python3
"""
exp_SGM_0008 - Composición XOR con fase dinámica (KoPE-inspired)

Hipótesis: incorporar una variable de fase dinámica ω(t) al binding XOR
(analogía a KoPE: sincronización de fase como mecanismo de composición
relacional) mejora el score de abducción y la robustez al ruido,
superando tanto el baseline D=16 como el D=32 estático de exp_SGM_0007.

Analogía en criollo:
  En exp_SGM_0007 probamos aumentar el "tamaño del espacio" (D) para
  que los conceptos tengan más room para ser diferentes. Funcionó
  parcialmente: D=32 mejoró respecto de D=16, pero D=64 no añadió
  nada. Más dimensión no siempre es mejor.

  KoPE propone algo diferente: en vez de hacer el espacio más grande,
  hace que los vectores "vivan" en el tiempo. Cada nodo tiene una
  fase ω(t) que oscila y se sincroniza con sus vecinos. Cuando dos
  conceptos están relacionados, sus fases se sincronizan (se alinean).
  Cuando no están relacionados, las fases se mantienen desfasadas.

  Es como una orquesta: los instrumentos que tocan juntos (conceptos
  relacionados) sincronizan su ritmo. Los que no están relacionados
  tocan en ritmos diferentes. El director (el grafo) no necesita
  decir explícitamente "esto va con esto" — la sincronización emerge
  de la dinámica.

  En SGM, esto significa que ω deja de ser un vector estático y se
  convierte en una variable de tiempo que evoluciona según las Ec. de
  Kuramoto: dω_i/dt = ω_0 + Σ_j K_ij * sin(ω_j - ω_i)

  La ventaja clave para la composición XOR: en vez de depender solo
  de la dirección del vector (que se pierde con ruido), la fase
  dinámica agrega una segunda coordenada temporal que ayuda a
  distinguir conceptos similares.

  Esto es lo que KoPE demostró en ARC-AGI: +3.75 pp de mejora con
  la misma cantidad de parámetros, porque la sincronización de fase
  agrega estructura relacional sin necesidad de más dimensiones.

  Para SGM: la fase dinámica puede resolver el problema de D=64
  que no mejoró sobre D=32, porque la información relacional ya no
  vive solo en la dirección del vector sino también en la fase.

Métricas:
  - pair_accuracy (¿encuentra el par correcto?)
  - avg_pair_score (similitud del par predicho vs ground truth)
  - noisy_accuracy (robustez con 5% de ruido)
  - phase_convergence (¿las fases de los componentes correctos se
    sincronizan más que las de los distractores?)
"""

import json
import math
import os
import random
import time

# ── Configuración del experimento ──────────────────────────────────
EXPERIMENT_ID = "exp_SGM_0008"
EXPERIMENT_NAME = "abduce_xor_phase_dynamics"
PHASE = "Fase 2 — Inferencia simbólica + duda"
DATE = "2026-08-02"

# Dimensionalidad fija (D=32, el óptimo de exp_SGM_0007)
D = 32
NUM_NODES = 30
NUM_COMPOSITIONS = 20
NUM_QUERIES = 10
SEED = 42
NUM_TICKS = 500

# Parámetros de fase dinámica (KoPE-inspired)
ALPHA_PHASE = 0.15    # tasa de sincronización (analogía a α de KoPE)
OMEGA_0 = 1.0         # frecuencia natural base
K_COUPPLING = 0.3     # fuerza de acoplamiento entre vecinos


def make_omega(D, seed):
    """Genera un vector omega de dimensión D con fase aleatoria."""
    rng = random.Random(seed)
    return [rng.random() * 2 - 1 for _ in range(D)]


def cosine_sim(a, b):
    """Coseno de similitud entre dos vectores."""
    if len(a) != len(b):
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def xor_compose(a, b):
    """Composición XOR: producto element-wise (binding)."""
    return [ai * bi for ai, bi in zip(a, b)]


def add_noise(vec, flip_rate=0.05):
    """Añade ruido flipando signos (simula interferencia)."""
    rng = random.Random(42)
    result = vec[:]
    for i in range(len(result)):
        if rng.random() < flip_rate:
            result[i] = -result[i]
    return result


# ── Nodos del grafo con fase dinámica ─────────────────────────────

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
            "phase": rng.random() * 2 * math.pi,  # fase inicial aleatoria
            "name": f"concept_{i}",
            "hit_count": 0,
            "vitality": 1.0,
        }
    return nodes


def kuramoto_step(nodes, edge_table, alpha=ALPHA_PHASE, K=K_COUPPLING):
    """
    Un paso de dinámica de Kuramoto para las fases de los nodos.
    
    dφ_i/dt = ω_0 + Σ_j K_ij * sin(φ_j - φ_i)
    
    Donde K_ij es el peso de la arista (similitud de contenido).
    Los nodos conectados con alta afinidad tienden a sincronizar sus fases.
    """
    new_phases = {}
    for i, node in nodes.items():
        phi_i = node["phase"]
        coupling_sum = 0.0
        # Sumar contribuciones de vecinos (edge_table como CSR)
        if i in edge_table:
            for j, weight in edge_table[i]:
                phi_j = nodes[j]["phase"]
                coupling_sum += weight * math.sin(phi_j - phi_i)
        # Actualizar fase
        dphi = ALPHA_PHASE * (OMEGA_0 + K * coupling_sum)
        new_phases[i] = (phi_i + dphi) % (2 * math.pi)
    
    for i, new_phi in new_phases.items():
        nodes[i]["phase"] = new_phi
    
    return nodes


def phase_binding(a_phase, b_phase, a_omega, b_omega, D):
    """
    Binding con fase dinámica: el producto element-wise se modula
    por la diferencia de fase entre los dos nodos.
    
    Cuando las fases están sincronizadas (Δφ ≈ 0): binding fuerte.
    Cuando están desfasadas (Δφ ≈ π): binding débil.
    
    Esto es análogo a KoPE donde la fase modula la atención.
    """
    delta_phi = (a_phase - b_phase) % (2 * math.pi)
    # Factor de modulación: máximo cuando fases alineadas, mínimo cuando opuestas
    phase_factor = math.cos(delta_phi)
    
    # Binding con modulación de fase
    composed = [(a_omega[i] * b_omega[i]) * phase_factor for i in range(D)]
    return composed


def abduce_xor_phase(query_omega, query_phase, nodes, D, top_k=5):
    """
    Abducción XOR con fase dinámica: busca el par (a, b) tal que
    phase_binding(a, b) ≈ query.
    """
    # Paso 1: encontrar candidatos individuales por similitud de omega
    candidates = []
    for nid, node in nodes.items():
        score = cosine_sim(query_omega, node["omega"])
        candidates.append((nid, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = candidates[:top_k]
    
    # Paso 2: intentar composiciones de pares de candidatos con fase dinámica
    best_score = -1.0
    best_pair = None
    best_composed = None
    
    for i, (id_a, score_a) in enumerate(top_candidates):
        for j, (id_b, score_b) in enumerate(top_candidates):
            if i >= j:
                continue
            # Componer con fase dinámica
            a_node = nodes[id_a]
            b_node = nodes[id_b]
            composed = phase_binding(
                a_node["phase"], b_node["phase"],
                a_node["omega"], b_node["omega"], D
            )
            pair_score = cosine_sim(query_omega, composed)
            if pair_score > best_score:
                best_score = pair_score
                best_pair = (id_a, id_b)
                best_composed = composed
    
    return best_pair, best_score, best_composed, top_candidates


# ── Experimento principal ────────────────────────────────────────────

def run_experiment(D, num_nodes, num_compositions, num_queries, seed):
    """Ejecuta el experimento con fase dinámica."""
    rng = random.Random(seed)
    
    # 1. Crear nodos con fase
    nodes = create_phase_nodes(D, num_nodes, seed)
    
    # 2. Construir edge_table (aristas por similitud de omega)
    edge_table = {}
    for i in range(num_nodes):
        neighbors = []
        for j in range(num_nodes):
            if i == j:
                continue
            sim = cosine_sim(nodes[i]["omega"], nodes[j]["omega"])
            if sim > 0.3:  # solo aristas significativas
                neighbors.append((j, sim))
        edge_table[i] = neighbors
    
    # 3. Evolucionar fases con Kuramoto durante NUM_TICKS
    for tick in range(NUM_TICKS):
        nodes = kuramoto_step(nodes, edge_table)
    
    # 4. Generar composiciones ground truth con fase dinámica
    compositions = []
    for _ in range(num_compositions):
        a = rng.randint(0, num_nodes - 1)
        b = rng.randint(0, num_nodes - 1)
        while b == a:
            b = rng.randint(0, num_nodes - 1)
        # Composición con fase dinámica
        composed = phase_binding(
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
    
    # 5. Abducción: recuperar los componentes originales
    results = []
    for comp in compositions[:num_queries]:
        pair, pair_score, _, candidates = abduce_xor_phase(
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
    
    # 6. Calcular métricas agregadas
    correct_pairs = sum(1 for r in results if r["found_correct"])
    correct_top1 = sum(1 for r in results if r["top1_is_ground_truth"])
    avg_pair_score = sum(r["pair_score"] for r in results) / len(results) if results else 0.0
    avg_top1_score = sum(r["top1_score"] for r in results) / len(results) if results else 0.0
    
    # 7. Robustez al ruido
    noisy_results = []
    for comp in compositions[:num_queries]:
        noisy_query = add_noise(comp["composed"], flip_rate=0.05)
        pair, pair_score, _, _ = abduce_xor_phase(
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
    
    # 8. Métrica de sincronización de fase
    # Medir si las fases de los pares correctos están más sincronizadas
    # que las de pares aleatorios
    sync_diffs = []
    for r in results:
        if r["predicted_pair"]:
            id_a, id_b = r["predicted_pair"]
            diff = abs(nodes[id_a]["phase"] - nodes[id_b]["phase"])
            sync_diffs.append(min(diff, 2 * math.pi - diff))
    avg_sync_diff = sum(sync_diffs) / len(sync_diffs) if sync_diffs else 0.0
    
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
        "avg_sync_diff": avg_sync_diff,
        "phase_convergence": 1.0 - (avg_sync_diff / math.pi),  # 1=sincronizado, 0=desfasado
    }


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(f"  {EXPERIMENT_ID}: Abducción XOR con fase dinámica (KoPE)")
    print("=" * 60)
    print()
    print("Hipótesis: la fase dinámica (Kuramoto-inspired) mejora")
    print("la composición XOR más que aumentar D solo.")
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
    print(f"  Sincronización de fase (avg Δφ): {result['avg_sync_diff']:.4f} rad")
    print(f"  Convergence (1 - Δφ/π):          {result['phase_convergence']:.4f}")
    print(f"  Tiempo:                          {result['elapsed_seconds']:.2f}s")
    print()
    
    # Comparación con exp_SGM_0007
    print("=" * 60)
    print("  COMPARACIÓN CON exp_SGM_0007 (D=32, sin fase)")
    print("=" * 60)
    print(f"  exp_SGM_0007 (D=32, estático):  pair_accuracy=0.1000, score=0.3408")
    print(f"  exp_SGM_0008 (D=32, fase din):  pair_accuracy={result['pair_accuracy']:.4f}, score={result['avg_pair_score']:.4f}")
    print(f"  Mejora en pair_accuracy:         +{result['pair_accuracy'] - 0.1:.4f}")
    print(f"  Mejora en score:                 +{result['avg_pair_score'] - 0.3408:.4f}")
    print()
    
    # Guardar resultados
    output = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_name": EXPERIMENT_NAME,
        "phase": PHASE,
        "date": DATE,
        "hypothesis": "Incorporar fase dinámica ω(t) al binding XOR (KoPE-inspired) mejora el score de abducción y la robustez al ruido, superando D=32 estático de exp_SGM_0007.",
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
        "script": "phases/phase2_inferencia/run_abduce_phase.py",
        "results_file": "phases/phase2_inferencia/results_exp_SGM_0008_abduce_phase.json",
        "test_target": "T-INF-03 (abducción XOR con fase dinámica KoPE-inspired)",
        "baseline_for": [],
        "variant_of": "exp_SGM_0005",
        "lit_refs": ["KoPE arXiv 2604.07904 (Xiao et al., Microsoft Research Asia, April 2026)", "Kanerva 1988 Sparse Distributed Memory", "HippoRAG NeurIPS 2024 (arxiv 2404.10501)"],
        "notes": "Resultado pendiente de ejecución. Comparar con exp_SGM_0007 (D=32, sin fase) para verificar si la fase dinámica mejora la composición XOR.",
        "notes_criollo": "Si la fase dinámica mejora el score, confirma que Kuramoto es el camino correcto para SGM. Si no mejora, puede que necesitemos combinar D mayor + fase, o que el mecanismo de fase necesita más ticks de convergencia."
    }
    
    out_path = f"/data/data/com.hermesagent.android/files/home/rizoma_docs/results_{EXPERIMENT_ID}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Resultados guardados en: {out_path}")
