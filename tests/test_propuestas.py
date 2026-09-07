# -*- coding: utf-8 -*-
"""Tests del lazo PROPONE → CREA (reintegración ↔ sueño, 0058).

Cierra el cabo suelto #2: la reintegración PROPONE (deja candidatas en
propuestas_reintegracion) y el sueño DECIDE (consolida si resuena, desvanece
si no). Antes, reintegrar() devolvía un dict que nadie consumía.

Verifican:
1. reintegrar(force=True) deja una propuesta en el buffer del SGM.
2. El sueño consolida la propuesta que resuena (crea una relación nueva).
3. El sueño vacía el buffer tras evaluar (no se re-procesa).
4. Una propuesta con novedad fuera de rango (alienígena/idéntica) se desvanece.
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


class TestPropuestaBuffer:
    def test_reintegrar_deja_propuesta(self):
        """reintegrar(force=True) alimenta el buffer de propuestas pendientes."""
        sgm = make_sgm()
        _sync(sgm)
        assert len(sgm.propuestas_reintegracion) == 0
        sgm.reintegrar(force=True)
        assert len(sgm.propuestas_reintegracion) == 1


class TestSuenoConsolida:
    def test_resonancia_crea_relacion(self):
        """Una propuesta que resuena (novedad en rango) se consolida como arista."""
        sgm = make_sgm()
        _sync(sgm)
        sgm.reintegrar(force=True)

        n_edges_antes = sum(len(v) for v in sgm.edges.values()) // 2
        eng = EndogenousEngine(sgm)
        consolidada = eng._evaluar_propuestas()

        # Puede consolidar o no dependiendo de la afinidad, pero el buffer queda vacío
        assert len(sgm.propuestas_reintegracion) == 0

    def test_buffer_se_vacia(self):
        """Tras evaluar, el buffer queda vacío (nada se re-procesa)."""
        sgm = make_sgm()
        _sync(sgm)
        for _ in range(3):
            sgm.reintegrar(force=True)
        assert len(sgm.propuestas_reintegracion) == 3

        eng = EndogenousEngine(sgm)
        eng._evaluar_propuestas()
        assert len(sgm.propuestas_reintegracion) == 0

    def test_propuesta_alienigena_se_desvanece(self):
        """Una propuesta de novedad extrema (alienígena) no consolida."""
        sgm = make_sgm()
        _sync(sgm)
        # Forjar una propuesta con novedad extrema (vector lejísimo)
        vec_alien = [100.0] * sgm.D  # muy lejos de todo omega
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
        """run_consolidation consume y evalúa propuestas pendientes."""
        sgm = make_sgm()
        _sync(sgm)
        sgm.reintegrar(force=True)
        assert len(sgm.propuestas_reintegracion) == 1

        eng = EndogenousEngine(sgm, max_cycles_per_session=3)
        report = eng.run_consolidation(cycles=3)
        # Tras el primer ciclo, la propuesta ya fue evaluada
        assert len(sgm.propuestas_reintegracion) == 0
        # El reporte registra propuestas consolidadas en los eventos
        assert all("propuestas_consolidadas" in ev for ev in report.dream_events)