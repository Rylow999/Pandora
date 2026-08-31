#!/usr/bin/env python3
"""
CLAMP — Intervención directa en estado de Pandora.

Permite forzar nodos, valencia, aislamiento, trauma, etc.
Para investigación: provocar estados y observar recuperación/patología.

Uso:
  python clamp.py --node=CONTROL --valence=-0.8 --isolation=true
  python clamp.py --trauma=0.7 --node=MEMORIA
  python clamp.py --reset
"""

import sys
import os
import argparse
import json

# Bootstrap: raíz del repo en sys.path antes de importar pandora (portátil)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pandora.core.pandora_agent import get_pandora_agent
from pandora.config.schemas import Intent


def clamp_node(agent, node_name: str, valence: float | None = None, 
               isolation: bool = False, trauma: float | None = None,
               doubt: float | None = None, contradiction: float | None = None):
    """
    Aplica clamp directo al SGM.
    """
    sgm = agent.sgm
    
    # Buscar nodo por nombre (en place_cells o por índice)
    target_idx = None
    
    # Buscar en place_cells
    for ctx, pid in sgm.place_cells.items():
        if node_name.upper() in ctx.upper():
            target_idx = pid
            break
    
    # Si no encontrado, buscar por concepto en omega (similitud semántica simple)
    if target_idx is None:
        # Mapeo simple de conceptos a índices conocidos
        concept_map = {
            "YO": 0, "OTRO": 1, "ENTORNO": 2, "CUERPO": 3,
            "MEMORIA": 4, "DUDA": 6, "MIEDO": 7, "CONTROL": 8,
            "PERDIDA": 9, "SEGURIDAD": 10, "CONTRADICCION": 29,
            "TRAUMA": 31
        }
        target_idx = concept_map.get(node_name.upper())
    
    if target_idx is None:
        print(f"[CLAMP] Nodo '{node_name}' no encontrado. Disponibles: YO, OTRO, ENTORNO, CUERPO, MEMORIA, DUDA, MIEDO, CONTROL, PERDIDA, SEGURIDAD, CONTRADICCION, TRAUMA")
        return False
    
    print(f"[CLAMP] Aplicando a nodo {target_idx} ({node_name})")
    
    # Aplicar cambios
    if valence is not None:
        # Valencia se refleja en vitalidad y homeostasis
        sgm.vitalidad[target_idx] = max(0.0, min(1.0, (valence + 1.0) / 2.0))
        print(f"  vitalidad[{target_idx}] = {sgm.vitalidad[target_idx]:.3f}")
    
    if isolation:
        # Aislar: remover todas las aristas del nodo
        if target_idx < len(sgm.edges):
            removed = len(sgm.edges[target_idx])
            sgm.edges[target_idx] = []
            # También remover referencias inversas
            for other in range(len(sgm.edges)):
                if target_idx in sgm.edges[other]:
                    sgm.edges[other].remove(target_idx)
            print(f"  Nodo aislado: {removed} aristas removidas")
    
    if trauma is not None:
        # Marcar trauma: reducir vitalidad drásticamente + flag
        sgm.vitalidad[target_idx] = max(0.0, sgm.vitalidad[target_idx] * (1.0 - trauma))
        if not hasattr(sgm, 'trauma_nodes'):
            sgm.trauma_nodes = set()
        if trauma > 0.5:
            sgm.trauma_nodes.add(target_idx)
        else:
            sgm.trauma_nodes.discard(target_idx)
        print(f"  Trauma aplicado: vitalidad={sgm.vitalidad[target_idx]:.3f}, trauma_nodes={sgm.trauma_nodes}")
    
    if doubt is not None:
        # Duda se refleja en status y V_grafo
        sgm.status = "INCONCLUSA" if doubt > 0.5 else "ACTIVA"
        if hasattr(sgm, 'V_grafo'):
            sgm.V_grafo = max(0.0, 1.0 - doubt)
        print(f"  status={sgm.status}, V_grafo={getattr(sgm, 'V_grafo', 'N/A')}")
    
    if contradiction is not None:
        # Contradicción directa
        sgm.status = "CONTRADICTORIA" if contradiction > 0.7 else ("INCONCLUSA" if contradiction > 0.3 else "ACTIVA")
        print(f"  status={sgm.status}")
    
    # Forzar recálculo de métricas
    agent.receive("")  # tick vacío para propagar
    
    print(f"[CLAMP] Completado. Estado SGM: modo={sgm.modo}, V_grafo={getattr(sgm, 'V_grafo', 'N/A')}, status={sgm.status}")
    return True


def reset_clamp(agent):
    """Resetea todos los clamps: restaura vitalidad, conexiones, status."""
    sgm = agent.sgm
    
    # Restaurar vitalidad base
    for i in range(len(sgm.vitalidad)):
        sgm.vitalidad[i] = 0.5
    
    # Recrear aristas base (conectividad aleatoria)
    import random
    rng = random.Random(42)
    sgm.set_edges({i: rng.sample(range(64), min(5, 63)) for i in range(64)})
    
    # Limpiar trauma
    if hasattr(sgm, 'trauma_nodes'):
        sgm.trauma_nodes.clear()
    
    # Reset status
    sgm.status = "ACTIVA"
    if hasattr(sgm, 'V_grafo'):
        sgm.V_grafo = 1.0
    
    print("[CLAMP] Reset completo aplicado")
    return True


def main():
    parser = argparse.ArgumentParser(description="Clamp directo en estado Pandora")
    parser.add_argument("--node", type=str, help="Nombre del nodo (YO, CONTROL, MEMORIA, etc.)")
    parser.add_argument("--valence", type=float, help="Valencia -1.0 a 1.0")
    parser.add_argument("--isolation", action="store_true", help="Aislar nodo (remover aristas)")
    parser.add_argument("--trauma", type=float, help="Nivel de trauma 0.0 a 1.0")
    parser.add_argument("--doubt", type=float, help="Nivel de duda 0.0 a 1.0")
    parser.add_argument("--contradiction", type=float, help="Nivel de contradicción 0.0 a 1.0")
    parser.add_argument("--reset", action="store_true", help="Resetear todos los clamps")
    parser.add_argument("--status", action="store_true", help="Mostrar estado actual")
    
    args = parser.parse_args()
    
    agent = get_pandora_agent()
    
    if args.status:
        print(json.dumps(agent.get_status(), indent=2))
        return
    
    if args.reset:
        reset_clamp(agent)
        return
    
    if not args.node and not args.reset:
        parser.error("--node requerido (o --reset)")
        return
    
    clamp_node(
        agent, 
        args.node,
        valence=args.valence,
        isolation=args.isolation,
        trauma=args.trauma,
        doubt=args.doubt,
        contradiction=args.contradiction
    )


if __name__ == "__main__":
    main()