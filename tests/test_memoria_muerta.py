# -*- coding: utf-8 -*-
"""Tests de la memoria de los muertos (NOTA 0073 paso 3).

Cuando un nodo muere (vitalidad -> 0), su información NO se borra: su omega +
vivencia pasan a un fondo residual, y un proceso nuevo puede reclutarla.
"""
import random
import tempfile
import os

from sgm.core.sgm_core import SGMAgentCore
from sgm.core.sgm_vivencia import FondoMemorial


class TestFondoMemorial:
    def test_enterrar_conserva_omega(self):
        fm = FondoMemorial(capacidad=4)
        fm.enterrar([0.1, 0.2, 0.3], {"veces_vivido": 5})
        assert len(fm.fondo) == 1
        assert fm.fondo[0]["omega"] == [0.1, 0.2, 0.3]
        assert fm.fondo[0]["vivencia"]["veces_vivido"] == 5

    def test_fondo_acotado(self):
        fm = FondoMemorial(capacidad=3)
        for i in range(5):
            fm.enterrar([i, i, i], {})
        assert len(fm.fondo) == 3  # solo conserva los últimos 3

    def test_reclutar_devuelve_mas_lejano(self):
        fm = FondoMemorial(capacidad=4)
        fm.enterrar([1.0, 0.0, 0.0], {})  # cerca de la referencia
        fm.enterrar([0.0, 0.0, 1.0], {})  # lejos de la referencia
        reclutados = fm.reclutar(excluir_omega=[1.0, 0.0, 0.0], k=1)
        # el más lejano a la referencia es el más 'nuevo'
        assert reclutados[0]["omega"] == [0.0, 0.0, 1.0]

    def test_envejecer_desvanece_viejos(self):
        fm = FondoMemorial(capacidad=3)
        fm.enterrar([1, 1, 1], {})
        for _ in range(4):  # envejecer más allá de la capacidad
            fm.envejecer()
        assert len(fm.fondo) == 0  # el muerto viejo se desvaneció


class TestMemoriaMuertaIntegrada:
    def test_nodo_muerto_pasa_al_fondo(self):
        sgm = SGMAgentCore(random.Random(42), D=64, n_nodes=16, gamma=0.01)
        sgm.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        # forzar la muerte de un nodo
        sgm.vitalidad[3] = 0.0
        sgm.reconciliar()
        assert len(sgm.memoria_muerta.fondo) > 0, "el nodo muerto debería pasar al fondo"

    def test_fondo_persiste(self):
        sgm = SGMAgentCore(random.Random(42), D=64, n_nodes=16, gamma=0.01)
        sgm.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        sgm.vitalidad[3] = 0.0
        sgm.reconciliar()
        assert len(sgm.memoria_muerta.fondo) > 0

        tmp = tempfile.mktemp(suffix=".npy")
        sgm.guardar(tmp)
        sgm2 = SGMAgentCore(random.Random(99), D=64, n_nodes=16, gamma=0.01)
        sgm2.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        sgm2.cargar(tmp)
        assert len(sgm2.memoria_muerta.fondo) == len(sgm.memoria_muerta.fondo)
        os.remove(tmp)