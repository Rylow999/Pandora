# -*- coding: utf-8 -*-
"""Tests de wiring: módulos previamente desconectados ya cableados.

Verifica que los módulos que estaban "escritos pero no cableados" ahora
están conectados al flujo real:
1. modelo_mundo / predecir_transicion se nutre y predice en step().
2. Metacognicion se importa y se instancia sobre el agente.
"""
import random

from sgm.core.sgm_core import SGMAgentCore
from sgm.core.sgm_metacognicion import Metacognicion


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


class TestModeloMundo:
    def test_modelo_mundo_se_nutre_en_step(self):
        """El modelo de mundo aprende transiciones durante step()."""
        sgm = make_sgm()
        for _ in range(25):
            sgm.step([0.1] * sgm.D, list(range(17)))
        # El modelo de mundo registró al menos una transición
        assert len(sgm.modelo_mundo) >= 1

    def test_predecir_transicion_devuelve_algo(self):
        """predecir_transicion es invocable y devuelve None o un siguiente estado."""
        sgm = make_sgm()
        for _ in range(15):
            sgm.step([0.1] * sgm.D, list(range(17)))
        # Tras aprender, puede predecir (o devolver None si no conoce la clave)
        p = sgm.predecir_transicion(sgm.ultimo_estado_q, 0)
        assert p is None or isinstance(p, int)


class TestMetacognicion:
    def test_metacognicion_importa(self):
        """Metacognicion se importa sin el import roto anterior."""
        sgm = make_sgm()
        meta = Metacognicion(sgm)
        assert meta is not None

    def test_metacognicion_reflexiona(self):
        """reflexionar devuelve un dict con confianza e incertidumbre."""
        sgm = make_sgm()
        meta = Metacognicion(sgm)
        meta.creencias["explorar"] = 0.8
        r = meta.reflexionar()
        assert isinstance(r, dict)
        assert "confianza_global" in r
        assert 0.0 <= r["confianza_global"] <= 1.0