# -*- coding: utf-8 -*-
"""Tests de la imaginación — proponer constelaciones contrafácticas (0058).

La imaginación es distinta del sueño (que re-recorre el SER) y del presente
(que ESCULPE). La imaginación PROPONE: recombina la zona activa con ruido en un
vector que no corresponde a ningún nodo existente ("qué pasaría si").

Verifican:
1. imaginar() produce un vector contrafáctico (distinto de todo omega existente).
2. No consolida ni esculpe nada (no toca co_activacion, consolidadas, edges).
3. La novedad es alta (se aleja del presente al que pertenece).
4. Sin presente activo, imaginar() devuelve vector vacío (no hay desde dónde).
"""
import math
import random

from sgm.core.sgm_core import SGMAgentCore


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


def _sync(sgm, steps=80):
    for _ in range(steps):
        sgm.step([0.1] * sgm.D, list(range(17)))


class TestImaginacionProduceContrafactico:
    def test_vector_es_distinto_de_todo_omega(self):
        """El vector imaginado no colapsa a ningún nodo existente (es 'no sido')."""
        sgm = make_sgm()
        _sync(sgm)
        res = sgm.imaginar()
        vec = res["vector"]

        distancias = [math.sqrt(sum((x - y) ** 2 for x, y in zip(vec, sgm.omega[n])))
                      for n in range(len(sgm.omega))]
        assert min(distancias) > 0.05, "el vector imaginado no debería ser un nodo existente"

    def test_vector_normalizado(self):
        """El vector imaginado está normalizado (||v|| ≈ 1)."""
        sgm = make_sgm()
        _sync(sgm)
        res = sgm.imaginar()
        vec = res["vector"]
        n = math.sqrt(sum(x * x for x in vec))
        assert abs(n - 1.0) < 1e-6

    def test_novedad_positiva(self):
        """La novedad (distancia al presente) es positiva y sustancial."""
        sgm = make_sgm()
        _sync(sgm)
        res = sgm.imaginar()
        assert res["novedad"] > 0.0


class TestImaginacionNoCommit:
    def test_no_toca_co_activacion(self):
        """Imaginar NO esculpe: la matriz de co-activación queda intacta."""
        sgm = make_sgm()
        _sync(sgm)
        antes = dict(sgm.co_activacion)
        sgm.imaginar()
        assert sgm.co_activacion == antes

    def test_no_toca_consolidadas_ni_edges(self):
        """Imaginar no consolida ni crea conexiones (eso es del sueño)."""
        sgm = make_sgm()
        _sync(sgm)
        antes_consolidadas = set(sgm.consolidadas)
        antes_edges = {k: list(v) for k, v in sgm.edges.items()}
        sgm.imaginar()
        assert set(sgm.consolidadas) == antes_consolidadas
        assert sgm.edges == antes_edges


class TestImaginacionSinPresente:
    def test_sin_zona_activa_devuelve_vacio(self):
        """Sin presente activo (todo vitalidad baja), no hay desde dónde imaginar."""
        sgm = make_sgm()
        # Colapsar vitalidad para que no haya zona activa
        for i in range(len(sgm.vitalidad)):
            sgm.vitalidad[i] = 0.0
        res = sgm.imaginar()
        assert res["vector"] == []
        assert res["seed"] == -1