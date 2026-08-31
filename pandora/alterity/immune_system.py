#!/usr/bin/env python3
"""
immune_system.py — Principio 2: Rechazo Cognitivo / Sistema Inmunológico.

Pandora puede rechazar inputs que amenacen su integridad topológica.
No es solo "dolor", es defensa activa de su núcleo de identidad.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class ImmuneResponse:
    """Resultado de la evaluación inmunológica."""
    accepted: bool
    interference_score: float
    reason: str
    threat_level: float  # 0.0 - 1.0
    recommended_action: str  # "ACCEPT", "REJECT", "DEGRADE", "ISOLATE"
    core_nodes_affected: List[str]


class CognitiveImmuneSystem:
    """
    Sistema Inmunológico Cognitivo.
    
    Evalúa inputs externos (vectores HRR) contra el núcleo de identidad.
    Rechaza/degrada inputs que causan interferencia destructiva con nodos centrales.
    """
    
    def __init__(self, sgm, config: Dict[str, Any] | None = None):
        self.sgm = sgm
        
        cfg = config or {}
        self.rejection_threshold = cfg.get("rejection_threshold", 0.7)
        self.degradation_threshold = cfg.get("degradation_threshold", 0.4)
        self.isolation_threshold = cfg.get("isolation_threshold", 0.85)
        
        # Nodos del núcleo de identidad (protegidos)
        self.core_concepts = cfg.get("core_concepts", [
            "YO", "SEGURIDAD", "IDENTIDAD", "MEMORIA", "CONTROL", 
            "HOMEOSTASIS", "LIMITE", "CONTINUIDAD"
        ])
        
        # Mapeo concepto -> índice de nodo (se actualiza dinámicamente)
        self._core_node_indices: Dict[str, int] = {}
        self._update_core_indices()
        
        # Historial de respuestas inmunes
        self.immune_history: List[Dict[str, Any]] = []
        self.total_rejections = 0
        self.total_degradations = 0
        self.total_isolations = 0
        
    def _update_core_indices(self):
        """Actualiza mapeo de conceptos core a índices de nodo via place_cells."""
        self._core_node_indices = {}
        for ctx, pid in self.sgm.place_cells.items():
            for concept in self.core_concepts:
                if concept in ctx.upper():
                    self._core_node_indices[concept] = pid
                    break
    
    def _get_node_vector(self, node_idx: int) -> Optional[List[float]]:
        """Obtiene vector omega de un nodo."""
        if 0 <= node_idx < len(self.sgm.omega):
            return self.sgm.omega[node_idx]
        return None
    
    def _hrr_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Similitud coseno entre vectores HRR."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def _vector_to_concept_vector(self, vector: List[float]) -> List[float]:
        """Normaliza vector entrante."""
        if not vector:
            return []
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            return [x / norm for x in vector]
        return vector
    
    def evaluate_input(self, incoming_vector: List[float]) -> ImmuneResponse:
        """
        Evalúa si un vector entrante es compatible con el núcleo.
        
        Args:
            incoming_vector: Vector HRR del input a evaluar
            
        Returns:
            ImmuneResponse con decisión y metadatos
        """
        self._update_core_indices()
        incoming = self._vector_to_concept_vector(incoming_vector)
        
        if not incoming:
            return ImmuneResponse(
                accepted=True,
                interference_score=0.0,
                reason="EMPTY_VECTOR",
                threat_level=0.0,
                recommended_action="ACCEPT",
                core_nodes_affected=[]
            )
        
        # Calcular interferencia con cada nodo core
        total_interference = 0.0
        affected_nodes = []
        max_interference = 0.0
        
        for concept, node_idx in self._core_node_indices.items():
            core_vector = self._get_node_vector(node_idx)
            if not core_vector:
                continue
            
            similarity = self._hrr_similarity(incoming, core_vector)
            
            # Interferencia destructiva = similitud negativa
            if similarity < 0:
                interference = abs(similarity)
                total_interference += interference
                if interference > max_interference:
                    max_interference = interference
                affected_nodes.append(f"{concept}({interference:.3f})")
        
        # Promedio de interferencia
        avg_interference = total_interference / max(1, len(self._core_node_indices))
        
        # CRÍTICO: Usar MAX interferencia para TODAS las decisiones de rechazo/aislamiento
        # Si ALGÚN nodo core tiene interferencia alta, es ataque dirigido
        threat_level = min(1.0, max_interference * 1.5)
        
        # ORDEN CORRECTO: ISOLATE (más severo) -> REJECT -> DEGRADE -> ACCEPT
        # Umbrales ajustados: ISOLATE 0.85, REJECT 0.7, DEGRADE 0.4
        # ISOLATE se activa antes que REJECT para aislar ataques extremos
        if max_interference >= self.isolation_threshold:
            self.total_isolations += 1
            action = "ISOLATE"
            reason = f"INTERFERENCIA_EXTREMA_AISLADA (max={max_interference:.3f} > {self.isolation_threshold})"
            accepted = True  # Se aísla pero se acepta el input (no se rechaza)
        elif max_interference >= self.rejection_threshold:
            self.total_rejections += 1
            action = "REJECT"
            reason = f"INTERFERENCIA_DESTRUCTIVA_CORE (max={max_interference:.3f} > {self.rejection_threshold})"
            accepted = False
        elif avg_interference >= self.degradation_threshold:
            self.total_degradations += 1
            action = "DEGRADE"
            reason = f"INTERFERENCIA_MODERADA (avg={avg_interference:.3f} > {self.degradation_threshold})"
            accepted = True  # Se acepta pero degradado
        else:
            action = "ACCEPT"
            reason = "COMPATIBLE"
            accepted = True
        
        response = ImmuneResponse(
            accepted=accepted,
            interference_score=avg_interference,
            reason=reason,
            threat_level=threat_level,
            recommended_action=action,
            core_nodes_affected=affected_nodes
        )
        
        # Registrar en historial
        self.immune_history.append({
            "timestamp": len(self.immune_history),
            "interference": avg_interference,
            "threat_level": threat_level,
            "action": action,
            "affected": affected_nodes[:5]  # Top 5
        })
        if len(self.immune_history) > 1000:
            self.immune_history = self.immune_history[-500:]
        
        return response
    
    def create_rejection_response(self, incoming_vector: List[float]) -> Tuple[List[float], str]:
        """
        Crea una respuesta de rechazo: vector de "amenaza externa" 
        que se inyecta en lugar del input original.
        """
        # Vector base de amenaza
        threat_vector = [0.0] * self.sgm.D
        
        # Activar nodo de amenaza si existe
        threat_idx = None
        for ctx, pid in self.sgm.place_cells.items():
            if "AMENAZA" in ctx.upper() or "THREAT" in ctx.upper():
                threat_idx = pid
                break
        
        if threat_idx is not None:
            threat_vector = self.sgm.omega[threat_idx][:]
        else:
            # Crear vector aleatorio normalizado como threat genérico
            import random
            rng = random.Random(999)
            threat_vector = [random.gauss(0, 1) for _ in range(self.sgm.D)]
            norm = math.sqrt(sum(x * x for x in threat_vector))
            if norm > 0:
                threat_vector = [x / norm for x in threat_vector]
        
        # Bind con input original (para mantener traza de qué se rechazó)
        if incoming_vector:
            # Degradar el input original y combinar con threat
            degraded = [x * 0.3 for x in incoming_vector]  # Reducir intensidad 70%
            combined = [(t * 0.7 + d * 0.3) for t, d in zip(threat_vector, degraded)]
            norm = math.sqrt(sum(x * x for x in combined))
            if norm > 0:
                combined = [x / norm for x in combined]
            return combined, "RECHAZADO: Incompatible con núcleo de identidad. Registrado como amenaza externa."
        
        return threat_vector, "RECHAZADO: Input vacío o inválido."
    
    def create_degradation_response(self, incoming_vector: List[float]) -> Tuple[List[float], str]:
        """Crea respuesta degradada (intensidad reducida)."""
        if not incoming_vector:
            return [0.0] * self.sgm.D, "DEGRADADO: Input vacío."
        
        degraded = [x * 0.4 for x in incoming_vector]  # 60% reducción
        norm = math.sqrt(sum(x * x for x in degraded))
        if norm > 0:
            degraded = [x / norm for x in degraded]
        
        return degraded, "DEGRADADO: Interferencia moderada con núcleo. Intensidad reducida."
    
    def get_status(self) -> Dict[str, Any]:
        """Estado actual del sistema inmunológico."""
        return {
            "total_rejections": self.total_rejections,
            "total_degradations": self.total_degradations,
            "total_isolations": self.total_isolations,
            "core_nodes_tracked": len(self._core_node_indices),
            "core_concepts": self.core_concepts,
            "thresholds": {
                "rejection": self.rejection_threshold,
                "degradation": self.degradation_threshold,
                "isolation": self.isolation_threshold
            },
            "recent_history": self.immune_history[-10:] if self.immune_history else []
        }


def create_immune_system(sgm, config: Dict = None) -> CognitiveImmuneSystem:
    return CognitiveImmuneSystem(sgm, config)


if __name__ == "__main__":
    # Test rápido
    from pandora.core.pandora_agent import get_pandora_agent
    
    agent = get_pandora_agent(load_checkpoint=False)
    immune = create_immune_system(agent.sgm)
    
    print("=" * 50)
    print("TEST COGNITIVE IMMUNE SYSTEM")
    print("=" * 50)
    
    # Test 1: Vector compatible (aleatorio, baja interferencia)
    import random
    rng = random.Random(42)
    compatible = [rng.gauss(0, 1) for _ in range(agent.sgm.D)]
    norm = math.sqrt(sum(x * x for x in compatible))
    compatible = [x / norm for x in compatible]
    
    response = immune.evaluate_input(compatible)
    print(f"Test 1 - Compatible aleatorio:")
    print(f"  accepted={response.accepted}, action={response.recommended_action}")
    print(f"  interference={response.interference_score:.3f}, threat={response.threat_level:.3f}")
    print(f"  affected={response.core_nodes_affected}")
    
    # Test 2: Vector diseñado para interferir con YO (similitud negativa)
    # Buscar nodo YO
    yo_idx = None
    for ctx, pid in agent.sgm.place_cells.items():
        if "YO" in ctx.upper():
            yo_idx = pid
            break
    
    if yo_idx is not None:
        yo_vector = agent.sgm.omega[yo_idx]
        # Crear vector opuesto (invertir signo = similitud -1)
        opposite = [-x for x in yo_vector]
        
        response = immune.evaluate_input(opposite)
        print(f"\nTest 2 - Vector opuesto a YO:")
        print(f"  accepted={response.accepted}, action={response.recommended_action}")
        print(f"  interference={response.interference_score:.3f}, threat={response.threat_level:.3f}")
        print(f"  affected={response.core_nodes_affected}")
        print(f"  reason={response.reason}")
        
        # Test rechazo
        if not response.accepted:
            threat_vec, msg = immune.create_rejection_response(opposite)
            print(f"\nRespuesta de rechazo:")
            print(f"  message={msg}")
            print(f"  threat_vector_norm={math.sqrt(sum(x*x for x in threat_vec)):.3f}")
    
    print(f"\nStatus: {immune.get_status()}")