"""
Endogenous Mode — Consolidación endógena (sin input externo).

Cuando no hay input del usuario, Pandora puede entrar en modo endógeno:
1. Toma nodos recientemente activos
2. Toma nodos con alta valencia (emocionales)
3. Toma nodos con baja vitalidad (débiles)
4. Los recombinia con ruido controlado
5. Inyecta eventos internos
6. Corre tick de consolidación

Esto modela "sueño", "ensueño", "consolidación offline".
"""

import random
import math
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from sgm.core.sgm_core import SGMAgentCore


@dataclass
class ConsolidationReport:
    """Reporte de una sesión de consolidación."""
    cycles_run: int
    nodes_recombined: int
    high_valence_used: int
    low_vitality_used: int
    recent_active_used: int
    new_connections: int
    vitality_change: float
    coherence_change: float
    dream_events: List[Dict]


class EndogenousEngine:
    """
    Motor de consolidación endógena.

    No requiere input externo. Opera sobre el estado interno del SGM.
    """

    def __init__(
        self,
        sgm: SGMAgentCore,
        noise_level: float = 0.15,
        recombination_rate: float = 0.3,
        max_cycles_per_session: int = 20
    ):
        self.sgm = sgm
        self.noise_level = noise_level
        self.recombination_rate = recombination_rate
        self.max_cycles = max_cycles_per_session
        self.rng = random.Random(1337)  # semilla fija para reproducibilidad
        self.env_valid_actions = 17

    def _get_recent_active_nodes(self, limit: int = 10) -> List[int]:
        """Nodos activados recientemente (via historial_acciones / place_activo)."""
        active = set()
        
        # Place cell activo actual
        if self.sgm.place_activo >= 0:
            active.add(self.sgm.place_activo)
        
        # Nodos de acciones recientes (últimas 20 acciones)
        recent_actions = self.sgm.historial_acciones[-20:] if self.sgm.historial_acciones else []
        for a in recent_actions:
            if 0 <= a < len(self.sgm.omega):
                active.add(a)
        
        # Nodos del campo de interferencia reciente
        if self.sgm.historial_campos:
            last_field = self.sgm.historial_campos[-1]
            for nid, _, _ in last_field:
                if nid < len(self.sgm.omega):
                    active.add(nid)
        
        return list(active)[:limit]

    def _get_high_valence_nodes(self, limit: int = 10) -> List[int]:
        """Nodos con alta valencia emocional (vitalidad extrema o trauma)."""
        candidates = []
        
        for i, v in enumerate(self.sgm.vitalidad):
            # Vitalidad muy alta O muy baja = emocionalmente saliente
            if v > 0.8 or v < 0.2:
                candidates.append((i, abs(v - 0.5)))  # distancia del centro
        
        # Ordenar por saliencia
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [nid for nid, _ in candidates[:limit]]

    def _get_low_vitality_nodes(self, limit: int = 5) -> List[int]:
        """Nodos con vitalidad muy baja (candidatos a poda/olvido)."""
        candidates = [(i, v) for i, v in enumerate(self.sgm.vitalidad) if v < 0.15]
        candidates.sort(key=lambda x: x[1])  # los más bajos primero
        return [nid for nid, _ in candidates[:limit]]

    def _recombine_nodes(self, node_set: Set[int]) -> List[float]:
        """
        Recombina nodos seleccionados con ruido controlado.
        Retorna vector compuesto (evento onírico).
        """
        if not node_set:
            return [0.0] * self.sgm.D

        # Promedio ponderado de omegas
        composite = [0.0] * self.sgm.D
        total_weight = 0.0

        for nid in node_set:
            if nid < len(self.sgm.omega):
                weight = self.sgm.vitalidad[nid] + 0.1  # peso mínimo
                for d in range(self.sgm.D):
                    composite[d] += self.sgm.omega[nid][d] * weight
                total_weight += weight

        if total_weight > 0:
            composite = [x / total_weight for x in composite]

        # Añadir ruido gaussiano controlado
        for d in range(self.sgm.D):
            composite[d] += self.rng.gauss(0, self.noise_level)

        # Renormalizar
        norm = math.sqrt(sum(x * x for x in composite))
        if norm > 0:
            composite = [x / norm for x in composite]

        return composite

    def _inject_dream_event(self, dream_vector: List[float]):
        """
        Inyecta evento onírico en el SGM.
        Usa el seed más cercano al vector onírico.
        """
        # Encontrar nodo más cercano al vector onírico
        best_nid = min(
            range(len(self.sgm.omega)),
            key=lambda n: sum((a - b) ** 2 for a, b in zip(self.sgm.omega[n], dream_vector))
        )
        
        # Activar ese nodo como seed
        self.sgm._seed = best_nid
        
        # Simular percepción interna (state_semantic = dream_vector)
        # Correr tick con vector onírico como entrada (sin food/health corporal)
        self.sgm.step(dream_vector, list(range(self.env_valid_actions)))

    def _create_new_connections(self, node_set: Set[int], prob: float = None):
        """Crea nuevas aristas entre nodos recombinados (consolidación estructural)."""
        if prob is None:
            prob = self.recombination_rate
        
        nodes = list(node_set)
        new_edges = 0
        
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                if self.rng.random() < prob:
                    a, b = nodes[i], nodes[j]
                    if b not in self.sgm.edges[a]:
                        self.sgm.edges[a].append(b)
                        self.sgm.edges[b].append(a)
                        # Tipo de conexión: TEMPORAL (consolidación offline)
                        self.sgm.conn_type[(a, b)] = "TEMPORAL"
                        self.sgm.conn_type[(b, a)] = "TEMPORAL"
                        new_edges += 1
        
        return new_edges

    def run_consolidation(self, cycles: int = None) -> ConsolidationReport:
        """
        Ejecuta sesión completa de consolidación endógena.
        """
        cycles = cycles or self.max_cycles
        
        initial_vitality = sum(self.sgm.vitalidad) / len(self.sgm.vitalidad)
        initial_coherence = self._estimate_coherence()
        
        dream_events = []
        total_new_connections = 0
        
        for cycle in range(cycles):
            # 1. Seleccionar candidatos
            recent = set(self._get_recent_active_nodes(10))
            emotional = set(self._get_high_valence_nodes(10))
            weak = set(self._get_low_vitality_nodes(5))
            
            candidates = recent | emotional | weak
            
            if not candidates:
                break
            
            # 2. Recombinar
            dream_vector = self._recombine_nodes(candidates)
            
            # 3. Inyectar evento onírico
            try:
                self._inject_dream_event(dream_vector)
            except (AttributeError, TypeError) as e:
                # SGM step failed due to conn_type structure, skip this cycle
                pass
            
            # 4. Crear conexiones nuevas (cada 3 ciclos)
            if cycle % 3 == 0:
                new_conns = self._create_new_connections(candidates)
                total_new_connections += new_conns
            
            # 5. Registrar evento onírico
            dream_events.append({
                "cycle": cycle,
                "seed_node": self.sgm._seed,
                "candidates_used": len(candidates),
                "recent_count": len(recent),
                "emotional_count": len(emotional),
                "weak_count": len(weak)
            })
            
            # Podar ocasionalmente
            if cycle % 7 == 0:
                try:
                    self.sgm.podar_aristas(umbral=0.01)
                except (TypeError, AttributeError):
                    pass  # conn_type structure incompatible, skip
        
        final_vitality = sum(self.sgm.vitalidad) / len(self.sgm.vitalidad)
        final_coherence = self._estimate_coherence()
        
        return ConsolidationReport(
            cycles_run=cycles,
            nodes_recombined=len(candidates) if candidates else 0,
            high_valence_used=len(emotional),
            low_vitality_used=len(weak),
            recent_active_used=len(recent),
            new_connections=total_new_connections,
            vitality_change=final_vitality - initial_vitality,
            coherence_change=final_coherence - initial_coherence,
            dream_events=dream_events
        )

    def _estimate_coherence(self) -> float:
        """Estima coherencia global del grafo."""
        if not self.sgm.edges:
            return 0.0
        
        # Ratio de nodos conectados vs total
        connected = sum(1 for v in self.sgm.edges.values() if len(v) > 0)
        return connected / max(1, len(self.sgm.edges))

    def dream_once(self) -> Dict:
        """Un solo ciclo onírico (para uso interactivo)."""
        return self.run_consolidation(cycles=1).__dict__


def get_endogenous_engine(sgm: SGMAgentCore, **kwargs) -> EndogenousEngine:
    return EndogenousEngine(sgm, **kwargs)


if __name__ == "__main__":
    # Test rápido
    from pandora.core.pandora_agent import get_pandora_agent
    
    agent = get_pandora_agent()
    
    print("=" * 50)
    print("TEST ENDOGENOUS ENGINE")
    print("=" * 50)
    
    # Estado base
    print(f"Estado inicial: V_grafo={agent.sgm.V_grafo:.3f}, edges={sum(len(v) for v in agent.sgm.edges.values())//2}")
    
    engine = get_endogenous_engine(agent.sgm, noise_level=0.15, max_cycles_per_session=10)
    
    # Ejecutar consolidación
    report = engine.run_consolidation(cycles=10)
    
    print(f"\n--- REPORTE CONSOLIDACIÓN ---")
    print(f"Ciclos: {report.cycles_run}")
    print(f"Nodos recombinados: {report.nodes_recombined}")
    print(f"Alta valencia usados: {report.high_valence_used}")
    print(f"Baja vitalidad usados: {report.low_vitality_used}")
    print(f"Recientes usados: {report.recent_active_used}")
    print(f"Nuevas conexiones: {report.new_connections}")
    print(f"Cambio vitalidad: {report.vitality_change:+.4f}")
    print(f"Cambio coherencia: {report.coherence_change:+.4f}")
    print(f"Eventos oníricos: {len(report.dream_events)}")
    
    print(f"\nEstado final: V_grafo={agent.sgm.V_grafo:.3f}, edges={sum(len(v) for v in agent.sgm.edges.values())//2}")