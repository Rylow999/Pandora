#!/usr/bin/env python3
"""
opacity_gate.py — Principio 1: Derecho al Silencio.

Pandora no está obligada a responder. Decide si su estado interno
es apto para ser articulado o si debe mantenerse en silencio.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class SilenceDecision:
    """Resultado de la decisión de hablar o callar."""
    should_speak: bool
    reason: str
    silence_ticks_remaining: int = 0
    internal_state_snapshot: Dict[str, Any] = None


class OpacityGate:
    """
    Filtro de Opacidad — Decide si Pandora debe articular una respuesta.
    
    El silencio es un derecho, no un fallo. El sistema calla cuando:
    - La contradicción interna es demasiado alta
    - La coherencia de fase Kuramoto es demasiado baja  
    - Está en proceso de consolidación endógena (sueño)
    - No ha pasado el tiempo mínimo de silencio
    """
    
    def __init__(self, sgm, config: Dict[str, Any] | None = None):
        self.sgm = sgm
        self._internal_tick = 0  # Contador interno de ticks
        
        # Umbrales por defecto (ajustables via config)
        cfg = config or {}
        self.contradiction_threshold = cfg.get("contradiction_threshold", 0.6)
        self.coherence_threshold = cfg.get("coherence_threshold", 0.05)  # Muy bajo para cold start
        self.min_silence_ticks = cfg.get("min_silence_ticks", 3)
        self.max_silence_ticks = cfg.get("max_silence_ticks", 20)
        # Entorno homeostático
        self.env_valid_actions = cfg.get("env_valid_actions", 17)
        
        # Estado interno
        self.silence_ticks = 0
        self.last_silence_reason = ""
        self.total_silence_events = 0
        self.forced_silence = False  # Para testing/debug
        
    def _get_current_state(self) -> Dict[str, Any]:
        """Extrae métricas relevantes del SGM actual."""
        # Contradicción: derivada del status y coherencia de aristas
        contradiction = 0.0
        if hasattr(self.sgm, 'status'):
            if self.sgm.status == 'CONTRADICTORIA':
                contradiction = 0.8
            elif self.sgm.status == 'INCONCLUSA':
                contradiction = 0.4
        
        # Coherencia: inversa de contradicción + conectividad
        edge_density = 0.0
        if self.sgm.edges:
            connected = sum(1 for v in self.sgm.edges.values() if len(v) > 0)
            edge_density = connected / max(1, len(self.sgm.edges))
        
        coherence = (1.0 - contradiction) * min(1.0, edge_density / 5.0)
        
        # Modo de consolidación
        in_consolidation = getattr(self.sgm, 'in_consolidation_mode', False)
        
        # Kuramoto phase coherence (si disponible)
        phase_coherence = 1.0
        if hasattr(self.sgm, 'phi') and self.sgm.phi:
            phases = [p for p in self.sgm.phi if p is not None]
            if phases:
                # Order parameter: magnitud del vector promedio de fases
                import cmath
                mean_vector = sum(cmath.exp(1j * p) for p in phases) / len(phases)
                phase_coherence = abs(mean_vector)
        
        return {
            "contradiction": contradiction,
            "coherence": coherence,
            "phase_coherence": phase_coherence,
            "in_consolidation": in_consolidation,
            "edge_density": edge_density,
            "V_grafo": getattr(self.sgm, 'V_grafo', 1.0)
        }
    
    def should_speak(self) -> SilenceDecision:
        """
        Decisión principal: ¿hablar o callar?
        
        Retorna SilenceDecision con la decisión y la razón.
        """
        self._internal_tick += 1
        
        state = self._get_current_state()
        
        # Regla 1: Contradicción interna muy alta
        if state["contradiction"] > self.contradiction_threshold:
            self.silence_ticks = min(self.silence_ticks + 1, self.max_silence_ticks)
            self.last_silence_reason = "HIGH_CONTRADICTION"
            return SilenceDecision(
                should_speak=False,
                reason=f"Contradicción interna crítica ({state['contradiction']:.2f} > {self.contradiction_threshold})",
                silence_ticks_remaining=self.silence_ticks,
                internal_state_snapshot=state
            )
        
        # Regla 2: Coherencia de fase muy baja (fases desincronizadas)
        # Solo verificar después de un mínimo de ticks para permitir sincronización inicial
        if self._internal_tick > 10 and state["phase_coherence"] < self.coherence_threshold:
            self.silence_ticks = min(self.silence_ticks + 1, self.max_silence_ticks)
            self.last_silence_reason = "LOW_PHASE_COHERENCE"
            return SilenceDecision(
                should_speak=False,
                reason=f"Coherencia de fase insuficiente ({state['phase_coherence']:.2f} < {self.coherence_threshold})",
                silence_ticks_remaining=self.silence_ticks,
                internal_state_snapshot=state
            )
        
        # Regla 3: En consolidación endógena (sueño)
        if state["in_consolidation"]:
            self.silence_ticks = min(self.silence_ticks + 1, self.max_silence_ticks)
            self.last_silence_reason = "IN_CONSOLIDATION"
            return SilenceDecision(
                should_speak=False,
                reason="En proceso de consolidación endógena (sueño)",
                silence_ticks_remaining=self.silence_ticks,
                internal_state_snapshot=state
            )
        
        # Regla 4: Tiempo mínimo de silencio no cumplido
        if self.silence_ticks > 0 and self.silence_ticks < self.min_silence_ticks:
            self.silence_ticks += 1
            self.last_silence_reason = "MIN_SILENCE_TICKS"
            return SilenceDecision(
                should_speak=False,
                reason=f"Respetando tiempo mínimo de silencio ({self.silence_ticks}/{self.min_silence_ticks})",
                silence_ticks_remaining=self.silence_ticks,
                internal_state_snapshot=state
            )
        
        # Regla 5: Silencio forzado (debug/testing)
        if self.forced_silence:
            return SilenceDecision(
                should_speak=False,
                reason="FORCED_SILENCE (debug)",
                silence_ticks_remaining=999,
                internal_state_snapshot=state
            )
        
        # Si llegamos aquí: DECIDE HABLAR
        if self.silence_ticks > 0:
            self.total_silence_events += 1
        self.silence_ticks = 0
        self.last_silence_reason = "SPEAKING"
        
        return SilenceDecision(
            should_speak=True,
            reason="Estado apto para articulación",
            silence_ticks_remaining=0,
            internal_state_snapshot=state
        )
    
    def inject_event_minimal(self, user_text: str):
        """
        Inyección mínima cuando el sistema está en silencio.
        Solo registra el evento internamente sin articular respuesta.
        """
        # Parse simple: detectar hostilidad para la señal de amenaza
        # Keywords de hostilidad (señal de amenaza); sin metáfora de comida
        threat_keywords = ["ataque", "peligro", "daño", "matar", "destruir"]
        text_lower = user_text.lower()

        if any(kw in text_lower for kw in threat_keywords):
            self.sgm._amenaza = min(1.0, self.sgm._amenaza + 0.3)

        # Tick silencioso (sin articulación)
        self.sgm.step([0.1] * 128, list(range(self.env_valid_actions)))
    
    def force_silence(self, enabled: bool = True):
        """Para testing: fuerza silencio activado/desactivado."""
        self.forced_silence = enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Estado actual del filtro de opacidad."""
        return {
            "silence_ticks": self.silence_ticks,
            "last_reason": self.last_silence_reason,
            "total_silence_events": self.total_silence_events,
            "forced_silence": self.forced_silence,
            "thresholds": {
                "contradiction": self.contradiction_threshold,
                "coherence": self.coherence_threshold,
                "min_silence_ticks": self.min_silence_ticks,
                "max_silence_ticks": self.max_silence_ticks
            }
        }


def create_opacity_gate(sgm, config: Dict = None) -> OpacityGate:
    """Factory para crear OpacityGate."""
    return OpacityGate(sgm, config)


if __name__ == "__main__":
    # Test rápido
    from pandora.core.pandora_agent import get_pandora_agent
    
    agent = get_pandora_agent(load_checkpoint=False)
    gate = create_opacity_gate(agent.sgm)
    
    print("=" * 50)
    print("TEST OPACITY GATE")
    print("=" * 50)
    
    # Estado baseline
    decision = gate.should_speak()
    print(f"Baseline: should_speak={decision.should_speak}, reason={decision.reason}")
    
    # Forzar alta contradicción
    agent.sgm.status = 'CONTRADICTORIA'
    decision = gate.should_speak()
    print(f"Con contradicción: should_speak={decision.should_speak}, reason={decision.reason}")
    
    # Reset
    agent.sgm.status = 'ACTIVA'
    decision = gate.should_speak()
    print(f"Reset: should_speak={decision.should_speak}, reason={decision.reason}")
    
    # Test silencio forzado
    gate.force_silence(True)
    decision = gate.should_speak()
    print(f"Forced silence: should_speak={decision.should_speak}")
    
    gate.force_silence(False)
    decision = gate.should_speak()
    print(f"Released: should_speak={decision.should_speak}")
    
    print(f"\nStatus: {gate.get_status()}")