# -*- coding: utf-8 -*-
"""Tests de la constelación como unidad (0057, opción Y).

La unidad de identidad es la matriz de co-activación (el ensamble), no el nodo.
co_activacion[(a,b)] cuenta cuántas veces a y b estuvieron ENCENDIDOS JUNTOS en
la zona activa (presente). La plasticidad decreciente emerge de esa densidad:
pares muy co-activados se consolidan — el clavo como Relation-R, no como nodo.

Verifican:
1. La co-activación se registra (la matriz crece con la actividad).
2. Solo entre pares conectados (no crea aristas nuevas: eso es del sueño).
3. Co-activación repetida consolida (plasticidad decreciente).
4. La matriz persiste (el ser sobrevive al reinicio).
"""
import math
import os
import random
import tempfile

from sgm.core.sgm_core import SGMAgentCore


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


class TestConstelacionRegistra:
    def test_matriz_crece_con_actividad(self):
        """La matriz de co-activación se puebla tras correr steps."""
        sgm = make_sgm()
        assert len(sgm.co_activacion) == 0
        for _ in range(60):
            sgm.step([0.1] * sgm.D, list(range(17)))
        assert len(sgm.co_activacion) > 0

    def test_solo_pares_conectados(self):
        """La co-activación NO crea aristas nuevas: solo pares ya en edges."""
        sgm = make_sgm()
        for _ in range(60):
            sgm.step([0.1] * sgm.D, list(range(17)))
        # Todo par co-activado debe existir en edges
        for (a, b) in sgm.co_activacion:
            assert b in sgm.edges.get(a, []) or a in sgm.edges.get(b, []), \
                f"par ({a},{b}) co-activado pero no conectado"

    def test_co_activacion_repetida_consolida(self):
        """Al alcanzar el umbral, el par co-activado entra en consolidadas (clavo)."""
        sgm = make_sgm()
        for _ in range(80):
            sgm.step([0.1] * sgm.D, list(range(17)))
        # Algún par muy co-activado debe haberse consolidado
        consolidados_por_coactivacion = {
            k for k, v in sgm.co_activacion.items() if v >= sgm.co_activacion_umbral
        }
        assert consolidados_por_coactivacion, "nada se consolidó por co-activación"
        for clave in consolidados_por_coactivacion:
            assert clave in sgm.consolidadas


class TestConstelacionPersiste:
    def test_matriz_survive_reinicio(self):
        """La matriz de co-activación (el ser) sobrevive a guardar/cargar."""
        sgm = make_sgm()
        for _ in range(60):
            sgm.step([0.1] * sgm.D, list(range(17)))

        tmp = tempfile.mktemp(suffix=".npy")
        try:
            sgm.guardar(tmp)
            sgm2 = make_sgm(seed=99)
            assert sgm2.cargar(tmp) is True
            assert set(sgm2.co_activacion.keys()) == set(sgm.co_activacion.keys())
            # Los valores se restauran igual
            for k, v in sgm.co_activacion.items():
                assert sgm2.co_activacion[k] == v
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


class TestPhilosofiaConstelacion:
    def test_clavo_emerge_como_densidad_no_como_declaracion(self):
        """El 'clavo' (nodo más co-activado) emerge del grafo, no se declara."""
        sgm = make_sgm()
        for _ in range(100):
            sgm.step([0.1] * sgm.D, list(range(17)))
        # El nodo más presente en la matriz de co-activación es un resultado
        # del proceso, no una elección a priori
        apariciones = {}
        for (a, b) in sgm.co_activacion:
            apariciones[a] = apariciones.get(a, 0) + sgm.co_activacion[(a, b)]
            apariciones[b] = apariciones.get(b, 0) + sgm.co_activacion[(a, b)]
        if apariciones:
            top_nodo = max(apariciones, key=apariciones.get)
            assert 0 <= top_nodo < len(sgm.omega)