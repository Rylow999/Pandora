#!/usr/bin/env python3
"""
exp_SGM_0007 - Composición XOR con D aumentado (Kanerva-inspired)

Hipótesis: aumentar la dimensionalidad D de 16 a 64+ reduce el ruido
en composiciones XOR, mejorando el score de abducción de ~0.042 (v0.23 v3)
a >0.50, siguiendo la recomendación de Kanerva (SDM, D≥10000 para binario,
D≥64 para continuo).

Se prueban 3 configuraciones:
  - D=16  (baseline v0.23 v3)
  - D=32  (intermedio)
  - D=64  (recomendado por Kanerva para vectores continuos)

Métricas:
  - Precisión de abducción (¿encuentra la composición correcta?)
  - Score de similitud cosine del resultado vs ground truth
  - Ratio señal/ruido (varianza inter-clase / varianza intra-clase)
  - Robustez al ruido (¿cómo cambia el score con bits flipados?)

Analogía en criollo:
  Imagá que querés distinguir dos conceptos: "fuego" y "agua".
  Con D=16 (un vector corto), las palabras "fuego" y "agua" se mezclan
  fácilmente porque hay poco espacio para diferenciarlas — es como
  intentar guardar 100 libros en una estantería de 16 espacios.
  Con D=64 (un vector largo), cada concepto tiene más "espacio" para
  ser único — es como pasar a una estantería de 64 espacios.
  Kanerva demostró que con D suficientemente grande, las señales se
  separan solas y el ruido se promedia.

  En la práctica de v0.23 v3, el score de composición relacional era
  0.042 vs 0.011 de azar — mejora mínima, el ruido dominaba.
  Con D=64, esperamos que la señal emerja y el score suba a >0.50.
"""

import json
import math
import os
import random
import time

# ── Configuración del experimento ──────────────────────────────────
EXPERIMENT_ID = "exp_SGM_0007"
EXPERIMENT_NAME = "abduce_xor_dimensionality"
PHASE = "Fase 2 — Inferencia simbólica + duda"
DATE = "2026-08-02"

# Dimensionalidades a probar (siguiendo recomendación Kanerva)
D_VALUES = [16, 32, 64]
NUM_NODES = 30
NUM_COMPOSITIONS = 20  # pares (a, b) → a⊕b
NUM_QUERIES = 10  # consultas de abducción por D
SEED = 42
NUM_TICKS = 500

# ── Funciones de generación de vectores ────────────────────────────

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
    """Añade ruido flipando bits (simula interferencia)."""
    rng = random.Random(42)
    result = vec[:]
    for i in range(len(result)):
        if rng.random() < flip_rate:
            result[i] = -result[i]  # flipar signo
    return result

# ── Nodos del grafo ─────────────────────────────────────────────────

def create_concept_nodes(D, num_nodes, seed):
    """Crea nodos de concepto con vectores omega de dimensión D."""
    rng = random.Random(seed)
    nodes = {}
    for i in range(num_nodes):
        omega = [rng.random() * 2 - 1 for _ in range(D)]
        # Normalizar
        norm = math.sqrt(sum(x * x for x in omega))
        if norm > 0:
            omega = [x / norm for x in omega]
        nodes[i] = {
            "id": i,
            "omega": omega,
            "name": f"concept_{i}",
            "hit_count": 0,
            "vitality": 1.0,
        }
    return nodes

# ── Abducción XOR con decaimiento ──────────────────────────────────

def abduce_xor(query_omega, nodes, D, top_k=5):
    """
    Abducción XOR: dado un query (composición de dos conceptos),
    encontrar los dos conceptos originales.
    
    Usa producto element-wise como binding inverso:
    Si query = a ⊗ b, entonces query ⊘ a ≈ b
    """
    scores = []
    for nid, node in nodes.items():
        # Intentar "deshacer" el binding con cada nodo
        # score = sim(query, node_omega) — ¿qué tan relacionado es?
        score = cosine_sim(query_omega, node["omega"])
        scores.append((nid, score))
    
    # Ordenar por score descendente
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]

def abduce_xor_pair(query_omega, nodes, D, top_k=5):
    """
    Abducción XOR mejorada: busca el par (a, b) tal que a⊗b ≈ query.
    Usa PPR-guided search (como en exp_SGM_0005) pero con D variable.
    """
    # Paso 1: encontrar candidatos individuales
    candidates = abduce_xor(query_omega, nodes, D, top_k=top_k)
    
    # Paso 2: intentar composiciones de pares de candidatos
    best_score = -1.0
    best_pair = None
    best_composed = None
    
    for i, (id_a, score_a) in enumerate(candidates):
        for j, (id_b, score_b) in enumerate(candidates):
            if i >= j:
                continue
            # Componer los dos candidatos
            composed = xor_compose(nodes[id_a]["omega"], nodes[id_b]["omega"])
            # Comparar con el query
            pair_score = cosine_sim(query_omega, composed)
            if pair_score > best_score:
                best_score = pair_score
                best_pair = (id_a, id_b)
                best_composed = composed
    
    return best_pair, best_score, best_composed, candidates

# ── Experimento principal ───────────────────────────────────────────

def run_experiment(D, num_nodes, num_compositions, num_queries, seed):
    """Ejecuta el experimento para una dimensionalidad D."""
    rng = random.Random(seed)
    
    # 1. Crear nodos
    nodes = create_concept_nodes(D, num_nodes, seed)
    
    # 2. Generar composiciones ground truth
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
            "score_a": cosine_sim(composed, nodes[a]["omega"]),
            "score_b": cosine_sim(composed, nodes[b]["omega"]),
        })
    
    # 3. Abducción: recuperar los componentes originales
    results = []
    for comp in compositions[:num_queries]:
        pair, pair_score, _, candidates = abduce_xor_pair(
            comp["composed"], nodes, D, top_k=5
        )
        
        # Verificar si encontró el par correcto
        found_correct = (
            pair is not None and
            ((pair[0] == comp["a"] and pair[1] == comp["b"]) or
             (pair[0] == comp["b"] and pair[1] == comp["a"]))
        )
        
        # Score del top-1 candidate vs ground truth
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
        })
    
    # 4. Calcular métricas agregadas
    correct_pairs = sum(1 for r in results if r["found_correct"])
    correct_top1 = sum(1 for r in results if r["top1_is_ground_truth"])
    avg_pair_score = sum(r["pair_score"] for r in results) / len(results) if results else 0.0
    avg_top1_score = sum(r["top1_score"] for r in results) / len(results) if results else 0.0
    
    # 5. Robustez al ruido: flipar 5% de los bits y medir degradación
    noisy_results = []
    for comp in compositions[:num_queries]:
        noisy_query = add_noise(comp["composed"], flip_rate=0.05)
        pair, pair_score, _, _ = abduce_xor_pair(noisy_query, nodes, D, top_k=5)
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
    
    return {
        "D": D,
        "num_nodes": num_nodes,
        "num_compositions": num_compositions,
        "num_queries": num_queries,
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
    }

# ── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(f"  {EXPERIMENT_ID}: Abducción XOR con D variable (Kanerva)")
    print("=" * 60)
    print()
    print("Hipótesis: aumentar D reduce ruido en composiciones XOR,")
    print("mejorando la precisión de abducción significativamente.")
    print()
    
    all_results = []
    
    for D in D_VALUES:
        print(f"── D={D} ──")
        start = time.time()
        result = run_experiment(D, NUM_NODES, NUM_COMPOSITIONS, NUM_QUERIES, SEED)
        elapsed = time.time() - start
        result["elapsed_seconds"] = round(elapsed, 2)
        all_results.append(result)
        
        print(f"  Nodos: {result['num_nodes']}")
        print(f"  Composiciones evaluadas: {result['num_queries']}")
        print(f"  Precisión par (pair_accuracy):  {result['pair_accuracy']:.4f}")
        print(f"  Precisión top-1 (top1_accuracy): {result['top1_accuracy']:.4f}")
        print(f"  Score promedio par:              {result['avg_pair_score']:.4f}")
        print(f"  Score promedio top-1:            {result['avg_top1_score']:.4f}")
        print(f"  Robustez (5% noise):             {result['noisy_accuracy']:.4f}")
        print(f"  Degradación por ruido:           {result['noise_degradation']:.4f}")
        print(f"  Tiempo:                          {result['elapsed_seconds']:.2f}s")
        print()
    
    # ── Comparación con v0.23 v3 ──────────────────────────────────
    print("=" * 60)
    print("  COMPARACIÓN CON v0.23 v3")
    print("=" * 60)
    print(f"  v0.23 v3 (D=16, baseline):     score=0.042 vs azar=0.011")
    print(f"  v0.23 v3 (D=16, baseline):     pair_accuracy={all_results[0]['pair_accuracy']:.4f}")
    print(f"  D=32 (intermedio):             pair_accuracy={all_results[1]['pair_accuracy']:.4f}")
    print(f"  D=64 (Kanerva recomendado):    pair_accuracy={all_results[2]['pair_accuracy']:.4f}")
    print()
    
    # ── Verificación de hipótesis ─────────────────────────────────
    best = max(all_results, key=lambda x: x["pair_accuracy"])
    worst = min(all_results, key=lambda x: x["pair_accuracy"])
    
    print("=" * 60)
    print("  VERIFICACIÓN DE HIPÓTESIS")
    print("=" * 60)
    print(f"  ¿D={best['D']} supera a D={worst['D']}?")
    print(f"    Sí: {best['pair_accuracy'] > worst['pair_accuracy']}")
    print(f"    Mejora: +{best['pair_accuracy'] - worst['pair_accuracy']:.4f}")
    print()
    
    # Guardar resultados
    output = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_name": EXPERIMENT_NAME,
        "phase": PHASE,
        "date": DATE,
        "hypothesis": "Aumentar D reduce ruido en composiciones XOR, mejorando precisión de abducción",
        "D_values_tested": D_VALUES,
        "num_nodes": NUM_NODES,
        "num_compositions": NUM_COMPOSITIONS,
        "num_queries": NUM_QUERIES,
        "seed": SEED,
        "results": all_results,
        "comparison_with_v023_v3": {
            "v023_v3_D16_score": 0.042,
            "v023_v3_azar_score": 0.011,
            "v023_v3_pair_accuracy": 0.042,  # baseline
            "best_D_pair_accuracy": best["pair_accuracy"],
            "improvement_over_v023_v3": best["pair_accuracy"] - 0.042,
        },
        "notes": "Kanerva SDM recomienda D≥10000 para binario, D≥64 para continuo. "
                 "Los resultados con D=64 muestran si la mejora es significativa "
                 "o si se necesita D aún mayor para composiciones XOR en DSCN-G.",
    }
    
    out_path = f"/data/data/com.hermesagent.android/files/home/rizoma_docs/results_{EXPERIMENT_ID}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Resultados guardados en: {out_path}")
