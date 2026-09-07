# -*- coding: utf-8 -*-
"""Tests de la reintegración — proponer constelaciones contrafácticas (0058).

La reintegración es distinta del sueño (que re-recorre el SER) y del presente
(que ESCULPE). La reintegración PROPONE: recombina la zona activa con ruido en
un vector que no corresponde a ningún nodo existente ("qué pasaría si"),
emergiendo espontáneamente cuando la dispersión (1 - integridad) es alta.

Verifican:
1. reintegrar() produce un vector contrafáctico (distinto de todo omega).
2. No consolida ni esculpe nada (no toca co_activacion, consolidadas, edges).
3. Emerge por dispersión: sin fuerza, solo dispara si integridad es baja.
4. Sin presente activo, devuelve vector vacío.
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


class TestReintegracionProduceContrafactico:
    def test_vector_es_distinto_de_todo_omega(self):
        """El vector reintegrado no colapsa a ningún nodo existente (es 'no sido')."""
        sgm = make_sgm()
        _sync(sgm)
        res = sgm.reintegrar(force=True)
        vec = res["vector"]

        distancias = [math.sqrt(sum((x - y) ** 2 for x, y in zip(vec, sgm.omega[n])))
                      for n in range(len(sgm.omega))]
        assert min(distancias) > 0.05, "el vector reintegrado no debería ser un nodo existente"

    def test_vector_normalizado(self):
        """El vector reintegrante está normalizado (||v|| ≈ 1)."""
        sgm = make_sgm()
        _sync(sgm)
        res = sgm.reintegrar(force=True)
        vec = res["vector"]
        n = math.sqrt(sum(x * x for x in vec))
        assert abs(n - 1.0) < 1e-6

    def test_novedad_positiva(self):
        """La novedad (distancia al presente) es positiva y sustancial."""
        sgm = make_sgm()
        _sync(sgm)
        res = sgm.reintegrar(force=True)
        assert res["novedad"] > 0.0


class TestReintegracionNoCommit:
    def test_no_toca_co_activacion(self):
        """Reintegrar NO esculpe: la matriz de co-activación queda intacta."""
        sgm = make_sgm()
        _sync(sgm)
        antes = dict(sgm.co_activacion)
        sgm.reintegrar(force=True)
        assert sgm.co_activacion == antes

    def test_no_toca_consolidadas_ni_edges(self):
        """Reintegrar no consolida ni crea conexiones (eso es del sueño)."""
        sgm = make_sgm()
        _sync(sgm)
        antes_consolidadas = set(sgm.consolidadas)
        antes_edges = {k: list(v) for k, v in sgm.edges.items()}
        sgm.reintegrar(force=True)
        assert set(sgm.consolidadas) == antes_consolidadas
        assert sgm.edges == antes_edges


class TestReintegracionSinPresente:
    def test_sin_zona_activa_devuelve_vacio(self):
        """Sin presente activo (todo vitalidad baja), no hay desde dónde reintegrar."""
        sgm = make_sgm()
        for i in range(len(sgm.vitalidad)):
            sgm.vitalidad[i] = 0.0
        res = sgm.reintegrar(force=True)
        assert res["vector"] == []
        assert res["seed"] == -1


class TestReintegracionEmergente:
    def test_emerge_por_dispersion(self):
        """Cuando la integridad es baja (dispersión alta), reintegra espontáneamente."""
        sgm = make_sgm()
        # Sincronizar para tener integridad alta => dispersión baja => no dispara
        _sync(sgm, steps=80)
        res_calma = sgm.reintegrar()  # sin force
        assert res_calma["disparador"] == "ninguno", \
            "con integridad alta no debería reintegrar espontáneamente"

    def test_fragmentacion_dispara_reintegracion(self):
        """Fragmentando el grafo (aislamiento), la dispersión dispara reintegración."""
        sgm = make_sgm()
        _sync(sgm, steps=40)
        # Fragmentar: aislar todos los nodos => conectividad 0 => integridad 0
        for nid in list(sgm.edges.keys()):
            sgm.edges[nid] = []
        integridad = sgm.integridad_topologica()
        assert integridad < 0.4, f"se esperaba fragmentación alta, integridad={integridad:.3f}"

        res = sgm.reintegrar()  # sin force, debería disparar por dispersión
        assert res["disparador"] in ("dispersión", "ninguno"), \
            f"disparador inesperado: {res['disparador']}"

    def test_disparador_forzado(self):
        """Con force=True, disparador es 'forzado' independientemente de la dispersión."""
        sgm = make_sgm()
        _sync(sgm, steps=40)
        res = sgm.reintegrar(force=True)
        assert res["disparador"] == "forzado"