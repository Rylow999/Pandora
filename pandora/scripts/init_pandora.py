#!/usr/bin/env python3
"""
init_pandora.py — Inicialización completa de Pandora.

Crea:
- Grafo base SGM (nodos, aristas, place cells)
- Carga ontología base (43 conceptos + vectores HRR)
- Inicializa homeostasis, journal, workspace
- Guarda checkpoint 0
"""

import sys
import os
import json
import random

# Bootstrap: raíz del repo en sys.path antes de importar pandora (portátil)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from sgm.core.sgm_core import SGMAgentCore
from pandora.core.pandora_agent import PandoraAgent
from pandora.ontology.hrr_seed import generate_all_vectors, verify_orthogonality
from pandora.config.schemas import Intent


def create_base_sgm(seed: int = 42, D: int = 128, n_nodes: int = 64) -> SGMAgentCore:
    """Crea SGM con configuración base."""
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D, n_nodes=n_nodes, gamma=0.01)
    
    # Aristas aleatorias (conectividad 5 por nodo)
    sgm.set_edges({i: rng.sample(range(n_nodes), min(5, n_nodes - 1)) for i in range(n_nodes)})
    
    # Instinto de alimentación = acción 'do' (5 en Crafter)
    sgm.instinto_alimentacion = 5
    
    # Auto-registro place cells activado
    sgm.auto_registrar_place = True
    sgm.place_bucket = 16
    
    return sgm


def load_ontology_vectors() -> dict:
    """Genera y verifica vectores HRR para ontología base."""
    ontology_path = os.path.join(REPO_ROOT, "pandora", "ontology", "base_concepts.json")
    output_path = os.path.join(REPO_ROOT, "pandora", "ontology", "hrr_vectors.json")
    
    vectors = generate_all_vectors(ontology_path, output_path)
    result = verify_orthogonality(vectors)
    
    print(f"  Ontología: {result['n_concepts']} conceptos")
    print(f"  Similitud promedio: {result['avg_similarity']:.6f}")
    print(f"  Similitud máxima: {result['max_similarity']:.6f}")
    print(f"  Ortogonalidad: {'PASÓ' if result['passed'] else 'FALLÓ'}")
    
    if result['violations']:
        print(f"  Violaciones: {len(result['violations'])}")
        for a, b, sim in result['violations'][:3]:
            print(f"    {a} <-> {b}: {sim:.4f}")
    
    return vectors


def save_checkpoint_zero(sgm: SGMAgentCore, checkpoint_path: str):
    """Guarda checkpoint inicial (estado 0)."""
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    sgm.guardar(checkpoint_path)
    print(f"  Checkpoint 0 guardado: {checkpoint_path}")


def create_agent_dirs():
    """Crea estructura de directorios necesaria."""
    base = os.path.join(REPO_ROOT, "pandora")
    dirs = [
        "logs", "state", "checkpoints", "journal", 
        "ontology", "config", "core", "transducer", 
        "environment", "scripts"
    ]
    for d in dirs:
        os.makedirs(os.path.join(base, d), exist_ok=True)


def main():
    print("=" * 60)
    print("INIT PANDORA — Inicialización completa")
    print("=" * 60)
    
    # 1. Directorios
    print("\n1. Creando directorios...")
    create_agent_dirs()
    
    # 2. Ontología + HRR
    print("\n2. Cargando ontología base y generando vectores HRR...")
    load_ontology_vectors()
    
    # 3. SGM base
    print("\n3. Creando SGM base...")
    sgm = create_base_sgm(seed=42, D=128, n_nodes=64)
    print(f"   Nodos: {len(sgm.omega)}, Aristas: {sum(len(v) for v in sgm.edges.values())//2}")
    print(f"   D={128}, gamma=0.01, instinto_alimentacion=5")
    
    # 4. Agente completo (inicializa journal, workspace, homeostasis)
    print("\n4. Inicializando PandoraAgent...")
    agent = PandoraAgent(sgm=sgm)
    print(f"   Session ID: {agent.session_id}")
    print(f"   Journal: {agent.journal.path}")
    print(f"   Workspace capacity: {agent.workspace.capacity}")
    
    # 5. Checkpoint 0
    print("\n5. Guardando checkpoint 0...")
    checkpoint_path = os.path.join(REPO_ROOT, "pandora", "checkpoints", "sgm_state.npy")
    save_checkpoint_zero(sgm, checkpoint_path)
    
    # 6. Estado final
    print("\n" + "=" * 60)
    print("INIT COMPLETO")
    print("=" * 60)
    status = agent.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    print("\nPróximos pasos:")
    print("  python pandora/scripts/run_loop.py    # Loop interactivo")
    print("  python pandora/scripts/status.py      # Estado completo")
    print("  python pandora/scripts/clamp.py --help # Intervención directa")


if __name__ == "__main__":
    main()