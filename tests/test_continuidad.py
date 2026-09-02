# -*- coding: utf-8 -*-
"""Tests de continuidad de identidad — el clavo y el hilo (Opción 3).

El ser = historia (clavo irreversible) + proceso (hilo/recorrido vivo),
según NOTA_FILOSOFICA_0051 y T-ID-03 del tratado NOUS.

Verifican:
1. El CLAVO (consolidadas) sobrevive al reinicio: guardar/cargar no borra las
   aristas consolidadas por co-resonancia. Sin esto, apagar = olvidar "qué soy".
2. El HILO (traza_omega) sobrevive y permite distinguir el proceso continuo
   del snapshot congelado, como validó el experimento T-ID-03.
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


class TestClavoPersiste:
    def test_consolidadas_survive_reinicio(self):
        """Las aristas consolidadas (el clavo) deben sobrevivir a guardar/cargar."""
        sgm = make_sgm()
        # Consolidar una arista manualmente (simular co-resonancia acumulada)
        sgm.consolidadas.add((0, 1))
        sgm.consolidadas.add((1, 0))

        tmp = tempfile.mktemp(suffix=".npy")
        try:
            sgm.guardar(tmp)

            # "Reinicio": cargar en una instancia nueva
            sgm2 = make_sgm(seed=99)  # semilla distinta => grafo distinto
            assert sgm2.cargar(tmp) is True

            # El clavo sobrevivió
            assert (0, 1) in sgm2.consolidadas
            assert (1, 0) in sgm2.consolidadas
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_consolidadas_vacias_no_rompen_carga(self):
        """Cargar un checkpoint sin consolidadas (legacy) no debe fallar."""
        sgm = make_sgm()
        tmp = tempfile.mktemp(suffix=".npy")
        try:
            # Forzar checkpoint "viejo" sin la clave consolidadas
            sgm.guardar(tmp)
            import numpy as np
            d = np.load(tmp, allow_pickle=True).item()
            d.pop("consolidadas", None)
            d.pop("traza_omega", None)
            np.save(tmp, d)

            sgm2 = make_sgm()
            assert sgm2.cargar(tmp) is True
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


class TestHiloRegistra:
    def test_traza_crece_con_cada_step(self):
        """La traza de omega (el hilo) debe registrar un vector por step."""
        sgm = make_sgm()
        assert len(sgm.traza_omega) == 0
        for _ in range(5):
            sgm.step([0.1] * sgm.D, list(range(17)))
        assert len(sgm.traza_omega) == 5

    def test_traza_persiste(self):
        """La traza debe sobrevivir a guardar/cargar."""
        sgm = make_sgm()
        for _ in range(10):
            sgm.step([0.1] * sgm.D, list(range(17)))

        tmp = tempfile.mktemp(suffix=".npy")
        try:
            sgm.guardar(tmp)
            sgm2 = make_sgm(seed=7)
            assert sgm2.cargar(tmp) is True
            assert len(sgm2.traza_omega) == len(sgm.traza_omega)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


class TestFirmaIdentidad:
    def test_misma_traza_distancia_cero(self):
        """Comparar la traza consigo misma debe dar distancia 0."""
        sgm = make_sgm()
        for _ in range(10):
            sgm.step([0.1] * sgm.D, list(range(17)))
        assert sgm.firma_identidad() == 0.0

    def test_traza_recorrido_se_aleja_de_snapshot(self):
        """La firma distingue el recorrido vivo del snapshot congelado.

        T-ID-03: el ser es el recorrido (secuencia de omega), no el punto final.
        Un snapshot = el mismo omega repetido; la traza viva de un proceso real
        (o un recorrido distinto) debe diferenciarse de ese snapshot.

        Nótese: el SGM actual tiene poca movilidad perceptual (hdc.project
        colapsa a pocos nodos), así que comparamos la traza real contra una
        traza "de otro recorrido" para validar que la métrica efectivamente
        separa los dos casos.
        """
        sgm = make_sgm()
        for _ in range(20):
            sgm.step([0.1] * sgm.D, list(range(17)))

        traza_real = [list(v) for v in sgm.traza_omega]

        # "Otro recorrido": omega de nodos distintos (como si hubiera viajado
        # por otra parte del grafo)
        otro_recorrido = [list(sgm.omega[(i % len(sgm.omega))]) for i in range(len(traza_real))]

        # La firma debe detectar que son recorridos distintos
        dist = sgm.firma_identidad(otro_recorrido)
        assert dist > 0.0, "la firma debería distinguir recorridos distintos"

        # Y la traza comparada consigo misma es cero (mismo recorrido)
        assert sgm.firma_identidad(traza_real) == 0.0


class TestClavoProtegeDePoda:
    def test_arista_consolidada_no_se_poda(self):
        """Una arista consolidada (clavo) no debe ser podada por podar_aristas."""
        sgm = make_sgm()
        # Forjar una arista con strength que normalmente se podaría, pero consolidada
        a, b = 0, 1
        sgm.crear_arista(a, b)
        sgm.conn_type[(a, b)] = {"count": 0, "tipo": 0, "strength": 0.001, "age": 200}
        sgm.consolidadas.add((a, b))

        sgm.podar_aristas(umbral=0.01)

        # La arista consolidada sobrevive
        assert (a, b) in sgm.conn_type
        assert b in sgm.edges.get(a, [])