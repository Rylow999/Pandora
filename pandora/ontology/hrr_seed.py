"""
Generador de vectores HRR determinísticos a partir de semillas fijas.

Usa la misma semilla base (1337) + semilla por concepto para reproducibilidad total.
No usa numpy (entorno stdlib puro) — implementación simple de vector aleatorio normalizado.
"""

import random
import math
import json
from pathlib import Path
from typing import List, Dict, Any


BASE_SEED = 1337
VECTOR_DIM = 1024


def hrr_random_vector(seed: int, dim: int = VECTOR_DIM) -> List[float]:
    """
    Genera vector aleatorio determinístico usando semilla compuesta.
    Distribución uniforme [-1, 1] normalizada a norma 1.
    """
    # Semilla compuesta: base + concepto para evitar colisiones
    composed_seed = BASE_SEED * 10000 + seed
    rng = random.Random(composed_seed)

    vec = [rng.uniform(-1.0, 1.0) for _ in range(dim)]

    # Normalizar a norma 1
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]

    return vec


def hrr_bind(v1: List[float], v2: List[float]) -> List[float]:
    """
    Binding HRR por convolución circular (aproximación simple).
    En implementación real usar FFT. Aquí versión O(n²) para claridad.
    """
    n = len(v1)
    result = [0.0] * n
    for i in range(n):
        s = 0.0
        for j in range(n):
            k = (i - j) % n
            s += v1[j] * v2[k]
        result[i] = s

    # Normalizar
    norm = math.sqrt(sum(x * x for x in result))
    if norm > 0:
        result = [x / norm for x in result]
    return result


def hrr_unbind(bound: List[float], v2: List[float]) -> List[float]:
    """Unbinding: convolución con inverso (aproximado por correlación)."""
    n = len(bound)
    result = [0.0] * n
    for i in range(n):
        s = 0.0
        for j in range(n):
            k = (i + j) % n
            s += bound[k] * v2[j]
        result[i] = s

    norm = math.sqrt(sum(x * x for x in result))
    if norm > 0:
        result = [x / norm for x in result]
    return result


def hrr_similarity(v1: List[float], v2: List[float]) -> float:
    """Similitud coseno entre vectores HRR."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(x * x for x in v1))
    norm2 = math.sqrt(sum(x * x for x in v2))
    if norm1 > 0 and norm2 > 0:
        return dot / (norm1 * norm2)
    return 0.0


def load_ontology(path: str) -> Dict[str, Any]:
    """Carga ontología base desde JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_all_vectors(ontology_path: str, output_path: str | None = None) -> Dict[str, List[float]]:
    """
    Genera vectores HRR para todos los conceptos en la ontología.
    Guarda en output_path si se proporciona.
    """
    ont = load_ontology(ontology_path)
    vectors = {}

    for concept in ont["concepts"]:
        cid = concept["id"]
        seed = concept["hrr_seed"]
        vectors[cid] = hrr_random_vector(seed)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "meta": {
                    "base_seed": BASE_SEED,
                    "vector_dim": VECTOR_DIM,
                    "generated_from": ontology_path
                },
                "vectors": vectors
            }, f, indent=2)

    return vectors


def verify_orthogonality(vectors: Dict[str, List[float]], threshold: float = 0.15) -> Dict[str, Any]:
    """
    Verifica cuasi-ortogonalidad: similitud entre pares distintos debería ser baja.
    Con dim=1024 y semillas independientes, esperamos ~0.03 promedio.
    """
    ids = list(vectors.keys())
    n = len(ids)
    max_sim = 0.0
    avg_sim = 0.0
    count = 0
    violations = []

    for i in range(n):
        for j in range(i + 1, n):
            sim = hrr_similarity(vectors[ids[i]], vectors[ids[j]])
            avg_sim += sim
            count += 1
            if sim > max_sim:
                max_sim = sim
            if sim > threshold:
                violations.append((ids[i], ids[j], sim))

    return {
        "n_concepts": n,
        "avg_similarity": avg_sim / count if count else 0,
        "max_similarity": max_sim,
        "threshold": threshold,
        "violations": violations,
        "passed": len(violations) == 0
    }


if __name__ == "__main__":
    # Generar y verificar
    ontology_path = "/home/delorien/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/pandora/ontology/base_concepts.json"
    output_path = "/home/delorien/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/pandora/ontology/hrr_vectors.json"

    print("Generando vectores HRR...")
    vectors = generate_all_vectors(ontology_path, output_path)
    print(f"Generados {len(vectors)} vectores (dim={VECTOR_DIM})")

    print("Verificando cuasi-ortogonalidad...")
    result = verify_orthogonality(vectors)
    print(f"  Conceptos: {result['n_concepts']}")
    print(f"  Similitud promedio: {result['avg_similarity']:.6f}")
    print(f"  Similitud máxima: {result['max_similarity']:.6f}")
    print(f"  Umbral: {result['threshold']}")
    print(f"  PASÓ: {result['passed']}")

    if result['violations']:
        print("  Violaciones:")
        for a, b, sim in result['violations'][:5]:
            print(f"    {a} <-> {b}: {sim:.4f}")

    # Guardar reporte
    report_path = "/home/delorien/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/pandora/ontology/hrr_verification.json"
    with open(report_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Reporte guardado en {report_path}")