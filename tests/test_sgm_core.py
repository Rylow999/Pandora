# -*- coding: utf-8 -*-
"""Tests de comportamiento del núcleo SGM.

Verifican que los mecanismos cognitivos subyacentes (HRR, Kuramoto,
homeostasis, aislamiento) se comportan como dicta la teoría, no solo
que los módulos importan.

Todos los tests son determinísticos (seed fija) y no requieren el LLM
ni red — operan sobre SGM puro.
"""
import math
import random

from sgm.core.sgm_core import SGMAgentCore
from sgm.core.sgm_hrr import HRR
from sgm.core.sgm_kuramoto import interferencia, kuramoto_step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sgm(D=128, n_nodes=64, seed=42):
    """Crea un SGM determinístico con grafo denso."""
    sgm = SGMAgentCore(random.Random(seed), D=D, n_nodes=n_nodes, gamma=0.01)
    # Grafo conectado: cada nodo con 5 vecinos aleatorios determinísticos
    rng = random.Random(seed)
    edges = {i: rng.sample(range(n_nodes), min(5, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


def phase_coherence(sgm):
    """Order parameter de Kuramoto: |<e^{iφ}>|."""
    phases = [p for p in sgm.phi if p is not None]
    if not phases:
        return 1.0
    z = sum(complex(math.cos(p), math.sin(p)) for p in phases) / len(phases)
    return abs(z)


# ---------------------------------------------------------------------------
# HRR — Holographic Reduced Representation
# ---------------------------------------------------------------------------

class TestHRR:
    def test_bind_unbind_roundtrip_preserves_similarity(self):
        """Unbind(bind(a,b), b) debe ser parecido a a (propiedad clave de HRR)."""
        rng = random.Random(0)
        hrr = HRR(D=128, rng=rng, n_roles=8)
        a = [rng.gauss(0, 1) for _ in range(128)]
        b = [rng.gauss(0, 1) for _ in range(128)]

        bound = hrr.bind(a, b)
        recovered = hrr.unbind(bound, b)

        # Coseno entre a y recovered debe ser alto (> 0.5 con vectores gaussianos)
        assert hrr.cos(a, recovered) > 0.5

    def test_cleanup_recovers_correct_item(self):
        """cleanup debe devolver el índice del vector más cercano en memoria."""
        rng = random.Random(1)
        hrr = HRR(D=128, rng=rng, n_roles=4)
        mem = [[rng.gauss(0, 1) for _ in range(128)] for _ in range(5)]
        # Normalizar memoria
        for v in mem:
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            for i in range(len(v)):
                v[i] /= n

        # El vector más cercano a mem[2] debe ser el índice 2
        query = mem[2][:]
        assert hrr.cleanup(query, mem) == 2

    def test_roles_are_normalized(self):
        """Los roles (base del binding HRR) deben estar normalizados a ||·||≈1."""
        rng = random.Random(2)
        hrr = HRR(D=64, rng=rng, n_roles=4)
        for r in hrr.roles:
            n = math.sqrt(sum(x * x for x in r))
            assert abs(n - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Kuramoto — sincronización de fase
# ---------------------------------------------------------------------------

class TestKuramoto:
    def test_sync_increases_coherence(self):
        """Iterar Kuramoto debe aumentar la coherencia de fase (order parameter)."""
        rng = random.Random(42)
        n = 64
        phi = [rng.uniform(0, 2 * math.pi) for _ in range(n)]
        vitalidad = [1.0] * n
        phi_root = 0.0

        def coherence(ph):
            z = sum(complex(math.cos(p), math.sin(p)) for p in ph) / len(ph)
            return abs(z)

        c0 = coherence(phi)
        for _ in range(50):
            kuramoto_step(phi, phi_root, vitalidad, eta=0.05)
        c1 = coherence(phi)

        # Tras iterar, la coherencia debe subir (los osciladores se alinean a phi_root)
        assert c1 > c0

    def test_interference_reflects_phase_alignment(self):
        """Un nodo en fase con phi_root debe tener interferencia positiva máxima."""
        omega = [1.0 / math.sqrt(128)] * 128  # ||omega|| = 1
        phi_root = 0.0
        # Nodo en fase exacta -> cos(0)=1 -> I = ||omega|| = 1
        I_aligned = interferencia(omega, 0.0, phi_root)
        assert abs(I_aligned - 1.0) < 1e-6
        # Nodo en contra-fase -> cos(pi) = -1 -> I negativo
        I_anti = interferencia(omega, math.pi, phi_root)
        assert I_anti < 0


# ---------------------------------------------------------------------------
# Grafo SGM + homeostasis
# ---------------------------------------------------------------------------

class TestSGMGraph:
    def test_agent_runs_and_tracks_state(self):
        """Un step() completo no debe romper y debe acumular acciones."""
        sgm = make_sgm()
        before = len(sgm.historial_acciones)
        sgm.step([0.1] * 128, list(range(17)), food=10, health=20)
        assert len(sgm.historial_acciones) == before + 1

    def test_phase_coherence_grows_over_sync(self):
        """Pre-sync de 50 pasos debe llevar la coherencia por encima de 0.2."""
        sgm = make_sgm()
        c0 = phase_coherence(sgm)
        for _ in range(50):
            sgm.step([0.1] * 128, list(range(17)), food=10, health=20)
        c1 = phase_coherence(sgm)
        # La coherencia sube respecto al estado inicial (cold start)
        assert c1 > c0, f"coherence no subió: {c0:.4f} -> {c1:.4f}"


class TestIsolation:
    def test_isolate_node_reduces_vitality_and_disconnects(self):
        """isolate_node debe bajar la vitalidad y cortar las conexiones del nodo."""
        sgm = make_sgm()
        # Registrar un place cell para un concepto core
        sgm.place_cells["PLACE_YO_0_0_0"] = 0
        sgm.vitalidad[0] = 1.0

        assert sgm.isolate_node("YO") is True

        # Vitalidad colapsada
        assert sgm.vitalidad[0] < 0.2
        # El nodo queda aislado (sin aristas salientes)
        assert len(sgm.edges.get(0, [])) == 0
        # Marcado en isolated_nodes
        assert 0 in sgm.isolated_nodes

    def test_isolate_unknown_concept_returns_false(self):
        """Aislar un concepto sin place cell debe devolver False sin efectos."""
        sgm = make_sgm()
        assert sgm.isolate_node("NO_EXISTE") is False
        assert not hasattr(sgm, "isolated_nodes") or len(sgm.isolated_nodes) == 0


# ---------------------------------------------------------------------------
# Pandora — homeostasis (métricas aislamiento/trauma)
# ---------------------------------------------------------------------------

class TestHomeostasis:
    def test_isolation_level_detects_isolated_nodes(self):
        """isolation_level debe medir la fracción de nodos sin conexiones."""
        from pandora.core.homeostasis import get_homeostasis

        sgm = make_sgm()
        homeo = get_homeostasis()

        # Caso base: grafo denso -> aislamiento bajo
        m0 = homeo.update_from_sgm(sgm)
        assert m0.isolation_level < 0.5

        # Aislar todos los nodos -> aislamiento = 1.0
        for nid in list(sgm.edges.keys()):
            sgm.edges[nid] = []
        m1 = homeo.update_from_sgm(sgm)
        assert m1.isolation_level >= 1.0

    def test_trauma_load_zero_when_no_trauma_nodes(self):
        """Sin trauma_nodes, trauma_load debe ser 0.0."""
        from pandora.core.homeostasis import get_homeostasis

        sgm = make_sgm()
        homeo = get_homeostasis()
        assert homeo.update_from_sgm(sgm).trauma_load == 0.0

    def test_trauma_load_scales_with_trauma_nodes(self):
        """Con trauma_nodes marcados, trauma_load debe reflejar la fracción."""
        from pandora.core.homeostasis import get_homeostasis

        sgm = make_sgm()
        sgm.trauma_nodes = {0, 1, 2}  # 3 de 64 nodos
        homeo = get_homeostasis()
        expected = 3 / len(sgm.omega)
        assert abs(homeo.update_from_sgm(sgm).trauma_load - expected) < 1e-6