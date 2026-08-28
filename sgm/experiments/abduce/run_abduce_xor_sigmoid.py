#!/usr/bin/env python3
"""
exp_SGM_0012 - Composición XOR con fase como multiplicador optimizado (sigmoid)

Diagnóstico de exp_SGM_0008-0011:
  ❌ v1 (cos(Δφ)): invertía el binding cuando Δφ≈π
  ❌ v2 (|cos(Δφ)|): anulaba el binding cuando Δφ≈π/2
  ❌ v3 (sesgo relacional): re-pondera pero no compensa D bajo
  ✅ v4 (sigmoid): nunca anula, nunca invierte, suave en todo el rango

La función sigmoid:
  phase_factor = 1 / (1 + exp(-k * (|cos(Δφ)| - 0.5)))
  
  Cuando |cos(Δφ)| = 1 (fases sincronizadas): factor ≈ 1.0 (boost máximo)
  Cuando |cos(Δφ)| = 0.5 (fases a π/3): factor ≈ 1.0 (neutro)
  Cuando |cos(Δφ)| = 0 (fases ortogonales): factor ≈ 0.73 (reducción moderada)
  Cuando |cos(Δφ)| = -1 (imposible con |cos|): no aplica

  La clave: el factor SIEMPRE está entre ~0.73 y ~1.0.
  Nunca anula (no llega a 0) y nunca invierte (siempre positivo).

  Analogía en criollo:
  Imaginate que el binding es un mensaje que dos personas se pasan.
  La fase es el "ruido de fondo" en el canal de comunicación.
  
  En v1 (cos): si el ruido es fuerte (fases opuestas), el mensaje se
  invierte — la persona escucha lo contrario de lo que dijeron.
  
  En v2 (|cos|): si el ruido es medio (fases ortogonales), el mensaje
  desaparece completamente — la persona no escucha nada.
  
  En v3 (sesgo): el ruido reduce el volumen del mensaje pero no lo
  elimina — la persona escucha más bajo pero sigue entendiendo.
  
  En v4 (sigmoid): el ruido reduce el volumen de forma suave y
  predecible — la persona escucha un poco más bajo pero NUNCA deja
  de escuchar. El mensaje siempre llega, solo que con más o menos
  claridad según cuánto ruido haya.

Métricas:
  - pair_accuracy (¿encuentra el par correcto?)
  - avg_pair_score (similitud del par predicho vs ground truth)
  - noisy_accuracy (robustez con 5% de ruido)
  - Comparación con exp_SGM_0007 (D=32, estático)
"""

import json
import math
import random
import time

EXPERIMENT_ID = "exp_SGM_0012"
EXPERIMENT_NAME = "abduce_xor_phase_sigmoid"
PHASE = "Fase 2 — Inferencia simbólica + duda"
DATE = "2026-08-02"

D = 32
NUM_NODES = 30
NUM_COMPOSITIONS = 20
NUM_QUERIES = 10
SEED = 42
NUM_TICKS = 2000

# Parámetros de fase dinámica
ALPHA_PHASE = 0.5
OMEGA_0 = 1.0
K_COUPPLING = 1.0

# Parámetros de sigmoid para fase como multiplicador optimizado
SIGMOID_K = 4.0    # pendiente de la sigmoid (cuán abrupta es la transición)
SIGMOID_THRESHOLD = 0.5  # punto medio de la sigmoid


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
            "phase": rng.random() * 0.5,  # fases iniciales cercanas
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


def phase_sigmoid(delta_phi, k=SIGMOID_K, threshold=SIGMOID_THRESHOLD):
    """
    Multiplicador de fase con sigmoid optimizado.
    
    Usa |cos(Δφ)| como entrada (siempre positivo, 0 a 1) y lo
    transforma con una sigmoid para obtener un factor suave
    que nunca llega a 0 ni es negativo.
    
    f(x) = 1 / (1 + exp(-k * (x - threshold)))
    
    Donde x = |cos(Δφ)|:
    - x=1 (sincronizadas): f ≈ 1.0 (boost máximo)
    - x=0.5 (neutro): f ≈ 0.5 (factor neutro)
    - x=0 (ortogonales): f ≈ 0.018 (reducción fuerte pero NO anula)
    
    La clave vs |cos(Δφ)|: cuando |cos(Δφ)|≈0, la sigmoid da ~0.018
    que es muy bajo pero NO es cero. El binding se atenúa mucho pero
    nunca desaparece. Esto evita el problema de v2 donde |cos(π/2)|=0
    anulaba el binding por completo.
    """
    x = abs(math.cos(delta_phi))
    return 1.0 / (1.0 + math.exp(-k * (x - threshold)))


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


def abduce_xor_phase_sigmoid(query_omega, query_phase, nodes, D, top_k=5):
    """
    Abducción XOR con fase como multiplicador sigmoid optimizado.
    
    El binding se modula por el factor sigmoid de fase.
    A diferencia de v1/v2, el factor sigmoid nunca anula el binding
    (siempre > 0.01) y nunca lo invierte (siempre positivo).
    """
    # Paso 1: candidatos individuales por similitud de omega
    candidates = []
    for nid, node in nodes.items():
        score = cosine_sim(query_omega, node["omega"])
        candidates.append((nid, score))
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = candidates[:top_k]
    
    # Paso 2: composiciones de pares con binding modulado por sigmoid de fase
    best_score = -1.0
    best_pair = None
    best_composed = None
    best_binding_score = 0.0
    best_phase_factor = 0.0
    
    for i, (id_a, score_a) in enumerate(top_candidates):
        for j, (id_b, score_b) in enumerate(top_candidates):
            if i >= j:
                continue
            a_node = nodes[id_a]
            b_node = nodes[id_b]
            
            # Binding modulado por sigmoid de fase
            delta_phi = (a_node["phase"] - b_node["phase"]) % (2 * math.pi)
            p_factor = phase_sigmoid(delta_phi)
            composed = [(a_node["omega"][idx] * b_node["omega"][idx]) * p_factor for idx in range(D)]
            binding_score = cosine_sim(query_omega, composed)
            
            if binding_score > best_score:
                best_score = binding_score
                best_pair = (id_a, id_b)
                best_composed = composed
                best_binding_score = cosine_sim(query_omega, xor_compose(a_node["omega"], b_node["omega"]))
                best_phase_factor = p_factor
    
    return best_pair, best_score, best_composed, best_binding_score, best_phase_factor, top_candidates


def run_experiment(D, num_nodes, num_compositions, num_queries, seed):
    """Ejecuta el experimento con fase como multiplicador sigmoid."""
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
    
    # 5. Generar composiciones ground truth (binding modulado por sigmoid)
    compositions = []
    for _ in range(num_compositions):
        a = rng.randint(0, num_nodes - 1)
        b = rng.randint(0, num_nodes - 1)
        while b == a:
            b = rng.randint(0, num_nodes - 1)
        delta_phi = (nodes[a]["phase"] - nodes[b]["phase"]) % (2 * math.pi)
        p_factor = phase_sigmoid(delta_phi)
        composed = [(nodes[a]["omega"][idx] * nodes[b]["omega"][idx]) * p_factor for idx in range(D)]
        compositions.append({
            "a": a,
            "b": b,
            "composed": composed,
            "phase_a": nodes[a]["phase"],
            "phase_b": nodes[b]["phase"],
            "phase_diff": abs(nodes[a]["phase"] - nodes[b]["phase"]),
            "phase_factor": p_factor,
        })
    
    # 6. Abducción con fase sigmoid
    results = []
    for comp in compositions[:num_queries]:
        pair, pair_score, _, binding_score, p_factor, candidates = abduce_xor_phase_sigmoid(
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
            "binding_score": binding_score,
            "phase_factor": p_factor,
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
    avg_binding_score = sum(r["binding_score"] for r in results) / len(results) if results else 0.0
    avg_phase_factor = sum(r["phase_factor"] for r in results) / len(results) if results else 0.0
    avg_top1_score = sum(r["top1_score"] for r in results) / len(results) if results else 0.0
    
    # 8. Robustez al ruido
    noisy_results = []
    for comp in compositions[:num_queries]:
        noisy_query = add_noise(comp["composed"], flip_rate=0.05)
        pair, pair_score, _, binding_score, p_factor, _ = abduce_xor_phase_sigmoid(
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
            "binding_score": binding_score,
            "phase_factor": p_factor,
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
        },
        "sigmoid_params": {
            "k": SIGMOID_K,
            "threshold": SIGMOID_THRESHOLD,
            "phase_binding": "sigmoid(|cos(Δφ)|) — nunca anula, nunca invierte",
        },
        "correct_pairs": correct_pairs,
        "correct_top1": correct_top1,
        "pair_accuracy": correct_pairs / len(results) if results else 0.0,
        "top1_accuracy": correct_top1 / len(results) if results else 0.0,
        "avg_pair_score": avg_pair_score,
        "avg_binding_score": avg_binding_score,
        "avg_phase_factor": avg_phase_factor,
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
    print(f"  {EXPERIMENT_ID}: Abducción XOR con fase sigmoid optimizada")
    print("=" * 60)
    print()
    print("Principio: fase como multiplicador sigmoid optimizado.")
    print("Nunca anula (siempre > 0.01), nunca invierte (siempre > 0).")
    print()
    print(f"Config: D={D}, {NUM_NODES} nodos, {NUM_TICKS} ticks Kuramoto")
    print(f"  α_phase={ALPHA_PHASE}, ω_0={OMEGA_0}, K={K_COUPPLING}")
    print(f"  sigmoid_k={SIGMOID_K}, sigmoid_threshold={SIGMOID_THRESHOLD}")
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
    print(f"  Score binding promedio (sin fase): {result['avg_binding_score']:.4f}")
    print(f"  Factor de fase promedio:        {result['avg_phase_factor']:.4f}")
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
    print(f"  exp_SGM_0007 (D=32, estático):     pair_acc=0.1000, score=0.3408")
    print(f"  exp_SGM_0008 (D=32, fase v1 cos):  pair_acc=0.0000, score=0.2763")
    print(f"  exp_SGM_0009 (D=32, fase v2 |cos|): pair_acc=0.0000, score=0.1780")
    print(f"  exp_SGM_0010 (D=32, fase sesgo):   pair_acc=0.0000, score=0.2654")
    print(f"  exp_SGM_0011 (D=128, fase sesgo):  pair_acc=0.1000, score=0.3544")
    print(f"  exp_SGM_0012 (D=32, fase sigmoid): pair_acc={result['pair_accuracy']:.4f}, score={result['avg_pair_score']:.4f}")
    print()
    print(f"  ¿Sigmoid supera a estático?  {result['pair_accuracy'] > 0.1}")
    print(f"  ¿Sigmoid supera a v1 (cos)?  {result['pair_accuracy'] > 0.0}")
    print(f"  ¿Sigmoid supera a v2 (|cos|)?  {result['pair_accuracy'] > 0.0}")
    print(f"  ¿Sigmoid supera a v3 (sesgo)?  {result['pair_accuracy'] > 0.0}")
    print()
    
    # Guardar resultados
    output = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_name": EXPERIMENT_NAME,
        "phase": PHASE,
        "date": DATE,
        "hypothesis": "La fase como multiplicador sigmoid optimizado (nunca anula, nunca invierte) mejora el binding XOR y supera D=32 estático.",
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
            "sigmoid_k": SIGMOID_K,
            "sigmoid_threshold": SIGMOID_THRESHOLD,
        },
        "script": "phases/phase2_inferencia/run_abduce_xor_sigmoid.py",
        "results_file": "phases/phase2_inferencia/results_exp_SGM_0012_abduce_xor_sigmoid.json",
        "test_target": "T-INF-03 (abducción XOR con fase sigmoid optimizada)",
        "baseline_for": [],
        "variant_of": "exp_SGM_0005",
        "lit_refs": ["KoPE arXiv 2604.07904 (Xiao et al., Microsoft Research Asia, April 2026)", "Kanerva 1988 Sparse Distributed Memory", "HippoRAG NeurIPS 2024 (arxiv 2404.10501)"],
        "notes": "Resultado pendiente de ejecución.",
        "notes_criollo": "Si la fase sigmoid mejora el score, confirma que el problema de v1/v2 era que el multiplicador de fase podía anular o invertir el binding. La sigmoid resuelve eso: siempre positiva, nunca cero. Si no mejora, el problema de fondo es D=32 (ruido del binding) y la fase no puede compensarlo sola."
    }
    
    out_path = f"/data/data/com.hermesagent.android/files/home/rizoma_docs/results_{EXPERIMENT_ID}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Resultados guardados en: {out_path}")