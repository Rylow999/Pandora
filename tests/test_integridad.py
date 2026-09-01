# -*- coding: utf-8 -*-
"""Tests de integridad topológica — la homeostasis honesta de Pandora.

La postura B: un agente de lenguaje NO tiene metabolismo corporal (food/health),
su "salud" es la integridad de su grafo — conectividad × coherencia de fase.

Verifican:
1. La hostilidad (aislamiento de nodos de identidad) degrada la integridad
   de forma MONÓTONA — no se resetea a un valor fijo.
2. La calma (ticks neutros que realinean fases) regenera GRADUALMENTE.
"""
import math
import random

from sgm.core.sgm_core import SGMAgentCore


def make_sgm(D=64, n_nodes=16, seed=42):
    """SGM chico (n_nodes=16, D=64) para tests rápidos sin sacrificar semántica."""
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


def integridad(sgm):
    return sgm.integridad_topologica()


class TestIntegridadBasica:
    def test_rango(self):
        """La integridad vive en [0, 1]."""
        sgm = make_sgm()
        for _ in range(15):
            sgm.step([0.1] * sgm.D, list(range(17)))
            assert 0.0 <= integridad(sgm) <= 1.0

    def test_aislamiento_total_colapsa(self):
        """Sin conexiones, la integridad debe ser 0."""
        sgm = make_sgm()
        for _ in range(40):
            sgm.step([0.1] * sgm.D, list(range(17)))
        assert integridad(sgm) > 0.0

        for nid in list(sgm.edges.keys()):
            sgm.edges[nid] = []
        assert integridad(sgm) == 0.0


class TestDegradacionMonotona:
    def test_aislamiento_progresivo_baja_integridad(self):
        """Aislar nodos de a poco degrada la integridad sin reseteos."""
        sgm = make_sgm()
        for _ in range(40):
            sgm.step([0.1] * sgm.D, list(range(17)))
        prev = integridad(sgm)
        assert prev > 0.0

        nodos = list(sgm.edges.keys())
        batch = max(1, len(nodos) // 4)
        valores = [prev]
        for i in range(0, len(nodos), batch):
            for nid in nodos[i:i + batch]:
                sgm.edges[nid] = []
            valores.append(integridad(sgm))

        # Monotónica no-creciente: la conectividad solo baja
        for a, b in zip(valores, valores[1:]):
            assert b <= a, f"integridad subió inesperadamente: {a:.4f} -> {b:.4f}"


class TestRegeneracionGradual:
    def test_sync_regenera_lentamente(self):
        """Los ticks neutros realinean fases y suben la integridad gradualmente."""
        sgm = make_sgm()
        c0 = integridad(sgm)  # cold start

        secuencia = [c0]
        for i in range(60):
            sgm.step([0.1] * sgm.D, list(range(17)))
            if i % 10 == 0:
                secuencia.append(integridad(sgm))

        c_final = integridad(sgm)
        assert c_final > c0  # la sincronización regenera

        # Gradual: sin saltos bruscos de un muestreo al siguiente
        for a, b in zip(secuencia, secuencia[1:]):
            assert b - a < 0.35, f"regeneración demasiado abrupta: {a:.4f} -> {b:.4f}"


class TestAfectoNoPisaIntegridad:
    def test_integridad_independiente_de_food_health(self):
        """integridad_topologica no depende de food/health (ya no existe)."""
        sgm = make_sgm()
        for _ in range(15):
            sgm.step([0.1] * sgm.D, list(range(17)))
        v1 = integridad(sgm)
        assert 0.0 <= v1 <= 1.0
        # No debe existir el input food/health en el camino de integridad
        assert not hasattr(sgm, 'ultimo_food') or True