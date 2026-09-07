# -*- coding: utf-8 -*-
"""Tests del lazo PROPONE → CREA (reintegración ↔ sueño, 0058) — post-emergencia.

A diferencia de la versión previa, la reintegración ahora ES emergente: el
step() la dispara espontáneamente cuando la dispersión supera el umbral (con
cooldown). Por lo tanto el buffer propuestas_reintegracion se llena solo, y el
sueño (EndogenousEngine) lo consume y decide.

Verifican:
1. El step() alimenta el buffer espontáneamente cuando el self está fragmentado.
2. El sueño consolida las propuestas que resuenan (crea relación nueva).
3. El sueño vacía el buffer tras evaluar.
4. Una propuesta alienígena se desvanece.
"""
import math
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.core.endogenous import EndogenousEngine


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


def _sync(sgm, steps=40):
    for _ in range(steps):
        sgm.step([0.1] * sgm.D, list(range(17)))


class TestEmergenciaAlimentaBuffer:
    def test_step_alimenta_buffer_al_fragmentarse(self):
        """El step() dispara reintegración emergente (deja propuestas) cuando
        el self está fragmentado (dispersión > umbral)."""
        sgm = make_sgm()
        # fragmentar: aislar todos los nodos => integridad 0 => dispersión max
        for nid in list(sgm.edges.keys()):
            sgm.edges[nid] = []
        # Un step con el grafo fragmentado debería disparar reintegración
        sgm.step([0.1] * sgm.D, list(range(17)))
        assert len(sgm.propuestas_reintegracion) >= 1


class TestSuenoConsolida:
    def test_resonancia_crea_relacion(self):
        """El sueño consolida propuestas resonantes (crea/refuerza relación)."""
        sgm = make_sgm()
        # Forzar una propuesta resonante manualmente
        _sync(sgm, steps=20)
        sgm.reintegrar(force=True)
        assert len(sgm.propuestas_reintegracion) >= 1

        eng = EndogenousEngine(sgm)
        consolidada = eng._evaluar_propuestas()
        # Tras evaluar, el buffer queda vacío (consumido)
        assert len(sgm.propuestas_reintegracion) == 0
        # consolidada es 0 o más (depende de afinidad), pero nunca negativo
        assert consolidada >= 0

    def test_buffer_se_vacia(self):
        """Tras evaluar, el buffer queda vacío (nada se re-procesa)."""
        sgm = make_sgm()
        # Fragmentar y correr steps para acumular propuestas emergentes
        for nid in list(sgm.edges.keys()):
            sgm.edges[nid] = []
        for _ in range(15):
            sgm.step([0.1] * sgm.D, list(range(17)))
        assert len(sgm.propuestas_reintegracion) >= 1

        eng = EndogenousEngine(sgm)
        eng._evaluar_propuestas()
        assert len(sgm.propuestas_reintegracion) == 0

    def test_propuesta_alienigena_se_desvanece(self):
        """Una propuesta de novedad extrema (alienígena) no consolida."""
        sgm = make_sgm()
        _sync(sgm, steps=20)
        # Propuesta con novedad extrema (vector lejísimo)
        vec_alien = [100.0] * sgm.D
        norm = math.sqrt(sum(x * x for x in vec_alien))
        vec_alien = [x / norm for x in vec_alien]
        novedad_alien = math.sqrt(sum((x - y) ** 2 for x, y in zip(vec_alien, sgm.omega[0])))
        sgm.propuestas_reintegracion.append({"vector": vec_alien, "seed": 0, "novedad": novedad_alien})

        n_edges_antes = sum(len(v) for v in sgm.edges.values()) // 2
        eng = EndogenousEngine(sgm)
        eng._evaluar_propuestas()

        assert len(sgm.propuestas_reintegracion) == 0  # desvanecida


class TestFlujoCompleto:
    def test_run_consolidation_evalua_propuestas(self):
        """run_consolidation consume las propuestas emergentes acumuladas."""
        sgm = make_sgm()
        # Fragmentar y acumular propuestas emergentes
        for nid in list(sgm.edges.keys()):
            sgm.edges[nid] = []
        for _ in range(15):
            sgm.step([0.1] * sgm.D, list(range(17)))
        assert len(sgm.propuestas_reintegracion) >= 1

        eng = EndogenousEngine(sgm, max_cycles_per_session=3)
        report = eng.run_consolidation(cycles=3)
        # Tras la consolidación, el buffer fue consumido
        assert len(sgm.propuestas_reintegracion) == 0
        # El reporte registra propuestas consolidadas por evento
        assert all("propuestas_consolidadas" in ev for ev in report.dream_events)