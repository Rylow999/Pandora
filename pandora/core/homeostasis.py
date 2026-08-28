"""
Homeostasis — métricas internas y estado sistémico de Pandora.

Mide: valence_mean, arousal_mean, doubt_level, contradiction_level,
coherence_level, isolation_level, trauma_load.

Clasifica estado global: STABLE | UNSTABLE | FRAGMENTED | CRITICAL
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import statistics


class SystemStatus(Enum):
    STABLE = "STABLE"
    UNSTABLE = "UNSTABLE"
    FRAGMENTED = "FRAGMENTED"
    CRITICAL = "CRITICAL"


@dataclass
class HomeostasisMetrics:
    """Métricas homeostáticas en un momento dado."""
    valence_mean: float = 0.0          # -1 a 1
    arousal_mean: float = 0.0          # 0 a 1
    doubt_level: float = 0.0           # 0 a 1
    contradiction_level: float = 0.0   # 0 a 1
    coherence_level: float = 1.0       # 0 a 1 (1 = totalmente coherente)
    isolation_level: float = 0.0       # 0 a 1
    trauma_load: float = 0.0           # 0 a 1 (acumulado)

    def to_dict(self) -> Dict[str, float]:
        return {
            "valence_mean": self.valence_mean,
            "arousal_mean": self.arousal_mean,
            "doubt_level": self.doubt_level,
            "contradiction_level": self.contradiction_level,
            "coherence_level": self.coherence_level,
            "isolation_level": self.isolation_level,
            "trauma_load": self.trauma_load
        }


class Homeostasis:
    """
    Monitor homeostático de Pandora.

    Recibe InternalState tras cada tick y actualiza métricas.
    Provee status global y alertas.
    """

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.history: List[HomeostasisMetrics] = []

        # Umbrales para clasificación de status
        self.thresholds = {
            "contradiction_critical": 0.7,
            "doubt_high": 0.6,
            "coherence_low": 0.3,
            "valence_very_negative": -0.5,
            "arousal_very_high": 0.8,
            "isolation_high": 0.7,
            "trauma_high": 0.5
        }

    def update(self, state) -> HomeostasisMetrics:
        """
        Actualiza métricas desde InternalState del SGM.
        """
        m = HomeostasisMetrics(
            valence_mean=getattr(state, 'valence', 0.0),
            arousal_mean=getattr(state, 'arousal', 0.0),
            doubt_level=getattr(state, 'doubt', 0.0),
            contradiction_level=getattr(state, 'contradiction', 0.0),
            coherence_level=1.0 - getattr(state, 'contradiction', 0.0),  # aprox
            isolation_level=0.0,  # calcular desde grafo si hay nodos aislados
            trauma_load=0.0       # calcular desde nodos con trauma
        )

        self.history.append(m)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        return m

    def update_from_sgm(self, sgm) -> HomeostasisMetrics:
        """
        Actualiza métricas extrayendo datos directamente del SGM.
        Más completo que solo InternalState.
        """
        # Valence: promedio de valencia de nodos activos / homeostáticos
        valence_vals = []
        for i, v in enumerate(sgm.vitalidad):
            if v > 0.1:
                # nodos con vitalidad significativa contribuyen
                pass

        # Usar homeostasis interna del SGM
        valence = 1.0 - getattr(sgm, '_hambre_real', 0.0) * 2
        arousal = getattr(sgm, '_amenaza', 0.0)

        # Doubt: del status del arbitro / dudas
        doubt = 1.0 - getattr(sgm, 'V_grafo', 1.0) if hasattr(sgm, 'V_grafo') else 0.0

        # Contradicción: desde sgm.status (ACTIVA/INCONCLUSA/CONTRADICTORIA)
        status = getattr(sgm, 'status', 'ACTIVA')
        contradiction = 0.8 if status == 'CONTRADICTORIA' else (0.3 if status == 'INCONCLUSA' else 0.0)

        # Coherencia: inversa de contradicción + factor de conectividad
        edge_density = sum(len(v) for v in sgm.edges.values()) / max(1, len(sgm.edges))
        coherence = (1.0 - contradiction) * min(1.0, edge_density / 10.0)

        # Isolation: nodos sin conexiones / total
        isolated = sum(1 for v in sgm.edges.values() if len(v) == 0)
        isolation = isolated / max(1, len(sgm.edges))

        # Trauma: nodos marcados como trauma (si existe atributo)
        trauma = 0.0
        if hasattr(sgm, 'trauma_nodes'):
            trauma = len(sgm.trauma_nodes) / max(1, len(sgm.omega))

        m = HomeostasisMetrics(
            valence_mean=valence,
            arousal_mean=arousal,
            doubt_level=doubt,
            contradiction_level=contradiction,
            coherence_level=coherence,
            isolation_level=isolation,
            trauma_load=trauma
        )

        self.history.append(m)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        return m

    def get_status(self) -> SystemStatus:
        """Clasifica estado global actual."""
        if not self.history:
            return SystemStatus.STABLE

        m = self.history[-1]
        t = self.thresholds

        # CRITICAL: contradicción alta O trauma alto O valencia muy negativa + arousal alta
        if (m.contradiction_level >= t["contradiction_critical"] or
            m.trauma_load >= t["trauma_high"] or
            (m.valence_mean <= t["valence_very_negative"] and m.arousal_mean >= t["arousal_very_high"])):
            return SystemStatus.CRITICAL

        # FRAGMENTED: coherencia baja O aislamiento alto
        if m.coherence_level <= t["coherence_low"] or m.isolation_level >= t["isolation_high"]:
            return SystemStatus.FRAGMENTED

        # UNSTABLE: duda alta O contradicción moderada
        if m.doubt_level >= t["doubt_high"] or m.contradiction_level >= 0.4:
            return SystemStatus.UNSTABLE

        return SystemStatus.STABLE

    def get_alert(self) -> Optional[str]:
        """Retorna mensaje de alerta si hay condición crítica."""
        status = self.get_status()
        if status == SystemStatus.CRITICAL:
            m = self.history[-1]
            if m.contradiction_level >= self.thresholds["contradiction_critical"]:
                return f"CONTRADICCIÓN CRÍTICA: {m.contradiction_level:.2f}"
            if m.trauma_load >= self.thresholds["trauma_high"]:
                return f"CARGA TRAUMÁTICA ALTA: {m.trauma_load:.2f}"
            return f"ESTADO CRÍTICO: valence={m.valence_mean:.2f}, arousal={m.arousal_mean:.2f}"
        elif status == SystemStatus.FRAGMENTED:
            m = self.history[-1]
            if m.coherence_level <= self.thresholds["coherence_low"]:
                return f"COHERENCIA BAJA: {m.coherence_level:.2f}"
            return f"AISLAMIENTO ALTO: {m.isolation_level:.2f}"
        elif status == SystemStatus.UNSTABLE:
            m = self.history[-1]
            if m.doubt_level >= self.thresholds["doubt_high"]:
                return f"DUDA ALTA: {m.doubt_level:.2f}"
            return f"CONTRADICCIÓN MODERADA: {m.contradiction_level:.2f}"
        return None

    def get_trends(self, window: int = 10) -> Dict[str, float]:
        """Tendencias recientes (pendiente lineal simple)."""
        if len(self.history) < 2:
            return {}

        recent = self.history[-window:]
        n = len(recent)
        trends = {}

        for key in ["valence_mean", "arousal_mean", "doubt_level", "contradiction_level", "coherence_level"]:
            vals = [getattr(m, key) for m in recent]
            if n >= 2:
                # pendiente simple: (último - primero) / (n-1)
                trends[key] = (vals[-1] - vals[0]) / (n - 1)
            else:
                trends[key] = 0.0

        return trends

    def summary(self) -> Dict:
        """Resumen completo para logging/debug."""
        if not self.history:
            return {"status": "STABLE", "metrics": {}, "alert": None, "trends": {}}

        m = self.history[-1]
        return {
            "status": self.get_status().value,
            "metrics": m.to_dict(),
            "alert": self.get_alert(),
            "trends": self.get_trends(),
            "history_len": len(self.history)
        }


def get_homeostasis(window_size: int = 50) -> Homeostasis:
    return Homeostasis(window_size)


if __name__ == "__main__":
    # Test rápido
    from pandora.config.schemas import InternalState, Intent

    h = get_homeostasis()

    # Simular estados
    states = [
        InternalState(active_nodes=["YO"], triplets=[], valence=0.1, arousal=0.1, doubt=0.1, contradiction=0.0, intent=Intent.RESPONDER),
        InternalState(active_nodes=["YO"], triplets=[], valence=-0.2, arousal=0.3, doubt=0.4, contradiction=0.1, intent=Intent.RESPONDER),
        InternalState(active_nodes=["YO"], triplets=[], valence=-0.6, arousal=0.5, doubt=0.7, contradiction=0.6, intent=Intent.EXPRESAR_ESTADO_INTERNO),
        InternalState(active_nodes=["YO"], triplets=[], valence=-0.8, arousal=0.9, doubt=0.8, contradiction=0.85, intent=Intent.EXPRESAR_ESTADO_INTERNO),
    ]

    print("=" * 50)
    print("TEST HOMEOSTASIS")
    print("=" * 50)

    for i, s in enumerate(states):
        m = h.update(s)
        summary = h.summary()
        print(f"\nTurno {i+1}:")
        print(f"  Status: {summary['status']}")
        print(f"  Valence: {m.valence_mean:.2f}, Arousal: {m.arousal_mean:.2f}")
        print(f"  Doubt: {m.doubt_level:.2f}, Contradiction: {m.contradiction_level:.2f}")
        print(f"  Coherence: {m.coherence_level:.2f}, Isolation: {m.isolation_level:.2f}")
        print(f"  Alert: {summary['alert']}")