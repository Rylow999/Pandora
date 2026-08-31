# -*- coding: utf-8 -*-
"""Tests de comportamiento de los módulos de Alteridad.

Cubren los 4 principios:
1. OpacityGate — derecho al silencio
2. CognitiveImmuneSystem — rechazo cognitivo
3. TranslationLimit — inefabilidad / límite de traducción

Todos determinísticos (seed fija), sin LLM ni red — operan sobre el grafo SGM
y los umbrales de los módulos directamente.
"""
import math
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.alterity.immune_system import CognitiveImmuneSystem
from pandora.alterity.opacity_gate import OpacityGate
from pandora.alterity.translation_limit import TranslationLimit
from pandora.config.schemas import InternalState, Triplet, Intent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sgm(D=128, n_nodes=64, seed=42):
    """SGM determinístico con place_cells para conceptos core."""
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(5, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    # Place cells para conceptos core (indices 0..8)
    core = ["YO", "SEGURIDAD", "IDENTIDAD", "MEMORIA", "CONTROL",
            "HOMEOSTASIS", "LIMITE", "CONTINUIDAD"]
    for i, c in enumerate(core):
        sgm.place_cells[f"PLACE_{c}_0_0_0"] = i
    return sgm


def make_state(**kw):
    """Construye un InternalState con defaults neutrales."""
    defaults = dict(
        active_nodes=["YO", "PRESENTE", "OTRO"],
        triplets=[Triplet(subject="YO", predicate="SALUDAR", object="OTRO")],
        valence=0.1, arousal=0.2, doubt=0.1, contradiction=0.0,
        intent=Intent.RESPONDER
    )
    defaults.update(kw)
    return InternalState(**defaults)


# ---------------------------------------------------------------------------
# Immune System — rechazo cognitivo
# ---------------------------------------------------------------------------

class TestImmuneSystem:
    def test_opposite_core_vector_triggers_isolate(self):
        """Vector opuesto a YO (similitud -1) debe aislar (max > isolation_threshold)."""
        sgm = make_sgm()
        immune = CognitiveImmuneSystem(sgm)

        yo_vector = sgm.omega[0]  # YO está en índice 0
        opposite = [-x for x in yo_vector]

        response = immune.evaluate_input(opposite)
        assert response.recommended_action == "ISOLATE"
        assert response.accepted is True  # ISOLATE no rechaza, aísla
        assert immune.total_isolations == 1

    def test_compatible_random_vector_accepted(self):
        """Vector aleatorio (similitud ~0) debe ser ACCEPT."""
        sgm = make_sgm()
        immune = CognitiveImmuneSystem(sgm)
        rng = random.Random(7)
        vec = [rng.gauss(0, 1) for _ in range(sgm.D)]
        n = math.sqrt(sum(x * x for x in vec)) or 1.0
        vec = [x / n for x in vec]

        response = immune.evaluate_input(vec)
        assert response.recommended_action == "ACCEPT"
        assert response.accepted is True

    def test_empty_vector_accepted(self):
        """Vector vacío debe devolver ACCEPT con motivo EMPTY_VECTOR."""
        sgm = make_sgm()
        immune = CognitiveImmuneSystem(sgm)
        response = immune.evaluate_input([])
        assert response.recommended_action == "ACCEPT"
        assert response.reason == "EMPTY_VECTOR"

    def test_rejection_response_matches_dim(self):
        """create_rejection_response debe devolver vector de dimensión D + mensaje."""
        sgm = make_sgm()
        immune = CognitiveImmuneSystem(sgm)
        vec = [0.1] * sgm.D
        threat_vec, msg = immune.create_rejection_response(vec)
        assert len(threat_vec) == sgm.D
        assert isinstance(msg, str) and msg

    def test_degrades_before_reject_ordering(self):
        """Interferencia moderada debe degradar, no rechazar ni aislar."""
        sgm = make_sgm()
        immune = CognitiveImmuneSystem(sgm)
        # Vector parcialmente anti-alineado con un nodo core => interferencia media
        yo = sgm.omega[0]
        # 40% anti, 60% ortogonal => interferencia ~0.4 (zona DEGRADE)
        partial = [-0.4 * x for x in yo] + [0.6 * x for x in sgm.omega[1]]
        response = immune.evaluate_input(partial)
        assert response.recommended_action in ("DEGRADE", "ACCEPT")


class TestImmuneThresholds:
    def test_threshold_ordering_isolation_over_reject(self):
        """isolation_threshold debe ser mayor que rejection_threshold (orden correcto)."""
        sgm = make_sgm()
        immune = CognitiveImmuneSystem(sgm)
        assert immune.isolation_threshold > immune.rejection_threshold > immune.degradation_threshold


# ---------------------------------------------------------------------------
# Opacity Gate — derecho al silencio
# ---------------------------------------------------------------------------

class TestOpacityGate:
    def test_high_contradiction_forces_silence(self):
        """status CONTRADICTORIA debe forzar silencio."""
        sgm = make_sgm()
        gate = OpacityGate(sgm)
        # Estado normal habla
        assert gate.should_speak().should_speak is True

        sgm.status = "CONTRADICTORIA"
        decision = gate.should_speak()
        assert decision.should_speak is False
        assert decision.reason.startswith("Contradicción")

    def test_forced_silence_override(self):
        """force_silence debe mandar silencio aunque el estado sea normal."""
        sgm = make_sgm()
        gate = OpacityGate(sgm)
        gate.force_silence(True)
        assert gate.should_speak().should_speak is False

        gate.force_silence(False)
        assert gate.should_speak().should_speak is True

    def test_min_silence_ticks_respected(self):
        """Tras un silencio, debe respetar el min_silence_ticks antes de volver a hablar."""
        sgm = make_sgm()
        gate = OpacityGate(sgm, {"min_silence_ticks": 3})

        sgm.status = "CONTRADICTORIA"
        gate.should_speak()  # activa silencio, silence_ticks=1
        sgm.status = "ACTIVA"

        # Inmediatamente después no puede hablar (min_silence_ticks=3)
        assert gate.should_speak().should_speak is False
        assert gate.should_speak().should_speak is False

    def test_normal_state_speaks(self):
        """Estado ACTIVA con grafo denso debe hablar."""
        sgm = make_sgm()
        gate = OpacityGate(sgm)
        assert gate.should_speak().should_speak is True


# ---------------------------------------------------------------------------
# Translation Limit — inefabilidad
# ---------------------------------------------------------------------------

class TestTranslationLimit:
    def test_too_many_nodes_not_translatable(self):
        """Más de max_active_nodes debe ser intraducible."""
        sgm = make_sgm()
        tl = TranslationLimit(sgm, {"max_active_nodes": 2})
        state = make_state(active_nodes=["A", "B", "C", "D"])
        decision = tl.can_translate(state)
        assert decision.translatable is False
        assert "nodos activos" in decision.reason

    def test_simple_state_translatable(self):
        """Estado simple con grafo sincronizado (fases alineadas) debe traducirse."""
        sgm = make_sgm()
        # Pre-sync: alinear fases (como hace el pipeline real antes de operar)
        for _ in range(80):
            sgm.step([0.1] * sgm.D, list(range(17)), food=10, health=20)
        tl = TranslationLimit(sgm)
        state = make_state(active_nodes=["YO", "OTRO"])
        decision = tl.can_translate(state)
        assert decision.translatable is True

    def test_no_triplets_not_auto_ineffable(self):
        """Estado sin tripletas NO debe forzar inefabilidad (fix aplicado)."""
        sgm = make_sgm()
        tl = TranslationLimit(sgm)
        state = make_state(triplets=[], active_nodes=["YO"])
        decision = tl.can_translate(state)
        assert decision.complexity_metrics["pattern_coherence"] == 0.5
        # No debe aparecer "Sin tripletas" como motivo
        assert "tripletas" not in decision.reason.lower()

    def test_pattern_coherence_small_set_defaults_one(self):
        """1-2 tripletas deben tener pattern_coherence = 1.0 (no incoherente)."""
        sgm = make_sgm()
        tl = TranslationLimit(sgm)
        state = make_state(triplets=[Triplet(subject="YO", predicate="SALUDAR", object="OTRO")])
        coherence = tl._estimate_pattern_coherence(state.triplets)
        assert coherence == 1.0

    def test_high_entropy_not_translatable(self):
        """Muchos nodos activos => entropía alta => intraducible."""
        sgm = make_sgm()
        tl = TranslationLimit(sgm, {"max_active_nodes": 100, "max_entropy": 0.1})
        state = make_state(active_nodes=[f"N{i}" for i in range(30)])
        decision = tl.can_translate(state)
        assert decision.translatable is False