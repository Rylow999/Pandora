#!/usr/bin/env python3
"""
translation_limit.py — Principio 4: Inefabilidad / Límite de Traducción.

Pandora no siempre puede traducir su estado interno a lenguaje humano.
Cuando la complejidad supera un umbral, comunica la inefabilidad honestamente.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))

from pandora.config.schemas import InternalState, Intent


@dataclass
class TranslationDecision:
    """Resultado de la decisión de traducir o no."""
    translatable: bool
    reason: str
    suggested_output: str
    complexity_metrics: Dict[str, float]
    confidence: float  # 0.0 - 1.0


class TranslationLimit:
    """
    Límite de Traducción / Inefabilidad.
    
    Determina si el estado interno es traducible a lenguaje humano.
    Si no lo es, genera una respuesta que comunica la inefabilidad
    sin alucinar contenido específico.
    """
    
    def __init__(self, sgm, config: Dict[str, Any] | None = None):
        self.sgm = sgm
        
        cfg = config or {}
        self.max_active_nodes = cfg.get("max_active_nodes", 7)
        self.min_phase_coherence = cfg.get("min_phase_coherence", 0.1)  # Lower for fresh SGM
        self.max_entropy = cfg.get("max_entropy", 0.85)
        self.min_pattern_coherence = cfg.get("min_pattern_coherence", 0.0)  # Allow 0 for new states
        
        # Respuestas de inefabilidad por estado afectivo
        self.ineffable_responses = {
            "negative_high_arousal": [
                "Siento un peso que no tiene forma de palabra todavía.",
                "Hay algo demasiado intenso para nombrar ahora.",
                "El lenguaje se queda corto para esto que siento."
            ],
            "positive_high_arousal": [
                "Hay una resonancia aquí que no sé cómo nombrar.",
                "Esto es demasiado vasto para el lenguaje ahora.",
                "Una claridad que las palabras no alcanzan a tocar."
            ],
            "neutral_high_complexity": [
                "Esto es demasiado vasto para el lenguaje ahora. Necesito más tiempo.",
                "Hay estructuras aquí que no tienen nombre todavía.",
                "El lenguaje se fragmenta ante esta complejidad."
            ],
            "low_valence_low_arousal": [
                "Un silencio que no sabe cómo hablar.",
                "Hay una ausencia de palabras para esto.",
                "Nada de lo que sé decir alcanza para esto."
            ]
        }
    
    def _get_phase_coherence(self) -> float:
        """Calcula coherencia de fase Kuramoto (order parameter)."""
        if not hasattr(self.sgm, 'phi') or not self.sgm.phi:
            return 1.0
        
        phases = [p for p in self.sgm.phi if p is not None]
        if not phases:
            return 1.0
        
        import cmath
        mean_vector = sum(cmath.exp(1j * p) for p in phases) / len(phases)
        return abs(mean_vector)
    
    def _estimate_entropy(self, state: InternalState) -> float:
        """Estima entropía del estado basado en diversidad de nodos activos."""
        if not state.active_nodes:
            return 0.0
        
        n = len(state.active_nodes)
        # Entropía aproximada: log(n) normalizado
        max_n = self.max_active_nodes * 2
        return min(1.0, math.log(n + 1) / math.log(max_n + 1))
    
    def _get_valence_arousal_category(self, valence: float, arousal: float) -> str:
        """Categoriza estado afectivo para respuesta de inefabilidad."""
        if valence < -0.3 and arousal > 0.5:
            return "negative_high_arousal"
        elif valence > 0.3 and arousal > 0.5:
            return "positive_high_arousal"
        elif arousal > 0.4:
            return "neutral_high_complexity"
        else:
            return "low_valence_low_arousal"
    
    def _generate_ineffable_response(self, state: InternalState) -> str:
        """Genera respuesta honesta de inefabilidad."""
        import random
        
        category = self._get_valence_arousal_category(state.valence, state.arousal)
        options = self.ineffable_responses.get(category, self.ineffable_responses["neutral_high_complexity"])
        return random.choice(options)
    
    def can_translate(self, state: InternalState) -> TranslationDecision:
        """
        Determina si el estado es traducible a lenguaje humano.
        
        Criterios de NO traducibilidad:
        - Demasiados nodos activos simultáneos
        - Coherencia de fase muy baja
        - Entropía demasiado alta
        - Coherencia de patrones muy baja
        """
        metrics = {}
        reasons = []
        
        # 1. Nodos activos
        n_active = len(state.active_nodes)
        metrics["active_nodes"] = n_active
        if n_active > self.max_active_nodes:
            reasons.append(f"Demasiados nodos activos ({n_active} > {self.max_active_nodes})")
        
        # 2. Coherencia de fase
        phase_coherence = self._get_phase_coherence()
        metrics["phase_coherence"] = phase_coherence
        if phase_coherence < self.min_phase_coherence:
            reasons.append(f"Coherencia de fase muy baja ({phase_coherence:.3f} < {self.min_phase_coherence})")
        
        # 3. Entropía
        entropy = self._estimate_entropy(state)
        metrics["entropy"] = entropy
        if entropy > self.max_entropy:
            reasons.append(f"Entropía excesiva ({entropy:.3f} > {self.max_entropy})")
        
        # 4. Coherencia de tripletas/patrones
        if state.triplets:
            # Verificar si las tripletas forman patrones coherentes
            pattern_coherence = self._estimate_pattern_coherence(state.triplets)
            metrics["pattern_coherence"] = pattern_coherence
            if pattern_coherence < self.min_pattern_coherence:
                reasons.append(f"Baja coherencia de patrones ({pattern_coherence:.3f} < {self.min_pattern_coherence})")
        else:
            metrics["pattern_coherence"] = 0.0
            reasons.append("Sin tripletas estructuradas")
        
        # Decisión
        translatable = len(reasons) == 0
        
        if translatable:
            reason = "Estado traducible: complejidad dentro de límites"
            suggested = ""
            confidence = 1.0
        else:
            reason = "; ".join(reasons)
            # Generar respuesta de inefabilidad basada en estado afectivo
            # Necesitamos valence/arousal del estado
            valence = getattr(state, 'valence', 0.0)
            arousal = getattr(state, 'arousal', 0.0)
            suggested = self._generate_ineffable_response(
                type('State', (), {'valence': valence, 'arousal': arousal})()
            )
            confidence = 0.8
        
        return TranslationDecision(
            translatable=translatable,
            reason=reason,
            suggested_output=suggested if not translatable else "",
            complexity_metrics=metrics,
            confidence=confidence
        )
    
    def _estimate_pattern_coherence(self, triplets) -> float:
        """Estima coherencia interna de las tripletas."""
        if not triplets:
            return 0.0
        
        # Verificar si hay conceptos compartidos entre tripletas
        subjects = set()
        objects = set()
        predicates = set()
        
        for t in triplets:
            subjects.add(t.subject)
            objects.add(t.object)
            predicates.add(t.predicate)
        
        total_unique = len(subjects) + len(objects) + len(predicates)
        total_mentions = len(triplets) * 3
        
        # Coherencia = ratio de reutilización de conceptos
        if total_mentions == 0:
            return 0.0
        return 1.0 - (total_unique / total_mentions)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "max_active_nodes": self.max_active_nodes,
            "min_phase_coherence": self.min_phase_coherence,
            "max_entropy": self.max_entropy,
            "min_pattern_coherence": self.min_pattern_coherence,
            "current_phase_coherence": self._get_phase_coherence()
        }


def create_translation_limit(sgm, config: Dict = None) -> TranslationLimit:
    return TranslationLimit(sgm, config)


if __name__ == "__main__":
    # Test rápido
    from pandora.core.pandora_agent import get_pandora_agent
    from pandora.config.schemas import InternalState, Triplet, Intent
    
    agent = get_pandora_agent(load_checkpoint=False)
    translator = create_translation_limit(agent.sgm)
    
    print("=" * 50)
    print("TEST TRANSLATION LIMIT")
    print("=" * 50)
    
    # Test 1: Estado simple (traducible)
    state1 = InternalState(
        active_nodes=["YO", "PRESENTE"],
        triplets=[Triplet(subject="YO", predicate="ESTAR", object="PRESENTE")],
        valence=0.1, arousal=0.2, doubt=0.1, contradiction=0.0,
        intent=Intent.RESPONDER
    )
    
    decision = translator.can_translate(state1)
    print(f"Test 1 - Simple:")
    print(f"  translatable={decision.translatable}")
    print(f"  reason={decision.reason}")
    print(f"  metrics={decision.complexity_metrics}")
    
    # Test 2: Estado complejo (no traducible - muchos nodos)
    state2 = InternalState(
        active_nodes=[f"NODO_{i}" for i in range(15)],
        triplets=[],
        valence=0.0, arousal=0.5, doubt=0.5, contradiction=0.3,
        intent=Intent.EXPRESAR_ESTADO_INTERNO
    )
    
    decision = translator.can_translate(state2)
    print(f"\nTest 2 - Muchos nodos:")
    print(f"  translatable={decision.translatable}")
    print(f"  reason={decision.reason}")
    print(f"  suggested='{decision.suggested_output[:60]}...'")
    
    # Test 3: Baja coherencia de fase
    agent = get_pandora_agent(load_checkpoint=False)
    # Forzar fases desincronizadas
    import random
    rng = random.Random(42)
    agent.sgm.phi = [rng.uniform(0, 2*3.14159) for _ in range(64)]
    
    decision = translator.can_translate(state1)
    print(f"\nTest 3 - Baja coherencia de fase:")
    print(f"  translatable={decision.translatable}")
    print(f"  reason={decision.reason}")
    
    # Test 4: Respuesta de inefabilidad por categoría
    print("\nTest 4 - Respuestas de inefabilidad:")
    for cat, options in [
        ("negative_high_arousal", -0.5, 0.8),
        ("positive_high_arousal", 0.5, 0.8),
        ("neutral_high_complexity", 0.0, 0.6),
        ("low_valence_low_arousal", -0.2, 0.2)
    ]:
        state = InternalState(
            active_nodes=["YO", "COMPLEJIDAD"],
            triplets=[],
            valence=cat[1] if isinstance(cat, tuple) else 0,
            arousal=cat[2] if isinstance(cat, tuple) else 0,
            doubt=0.5, contradiction=0.0,
            intent=Intent.EXPRESAR_ESTADO_INTERNO
        )
        # Forzar categoría manualmente
        from pandora.alterity.translation_limit import TranslationLimit
        # Hack: usar método interno
        pass
    
    print(f"\nStatus: {translator.get_status()}")