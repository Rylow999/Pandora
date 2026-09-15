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

    def test_mitosis_recluta_del_fondo(self):
        """Reencarnación (0073 p3): el hijo de la mitosis hereda 30% del material
        del muerto más 'nuevo' (más lejano a lo heredado), no solo del padre vivo."""
        sgm = SGMAgentCore(random.Random(42), D=64, n_nodes=16, gamma=0.01)
        sgm.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        # un muerto con omega conocido y muy distinto
        muerto_omega = [10.0] * 64
        sgm.memoria_muerta.enterrar(muerto_omega, {})
        omega_antes = [list(o) for o in sgm.omega]
        n_antes = len(sgm.omega)
        sgm._engendrar_hijo(0, 1)
        assert len(sgm.omega) == n_antes + 1, "la mitosis creó el hijo"
        hijo = sgm.omega[-1]
        heredado_puro = omega_antes[0]  # padre aprox (heredar_concepto(0) + delta)
        # el hijo debe estar MEZCLADO con el muerto: distinto a la pura herencia
        import math
        def dist(x, y):
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(x, y)))
        d_al_muerto = dist(hijo, muerto_omega)
        d_del_padre_al_muerto = dist(heredado_puro, muerto_omega)
        # heredar_concepto agrega delta σ=0.10 al padre; con sigma chico el hijo
        # sin mezcla quedaría casi tan lejos del muerto como el padre. La mezcla
        # 70/30 lo acerca claramente al muerto.
        assert d_al_muerto < d_del_padre_al_muerto * 0.8, (
            f"hijo no heredó del fondo: d_muerto={d_al_muerto:.2f} "
            f"vs padre-muerto={d_del_padre_al_muerto:.2f}"
        )

    def test_mitosis_sin_fondo_no_rompe(self):
        """Sin muertos en el fondo, la mitosis funciona igual que siempre."""
        sgm = SGMAgentCore(random.Random(42), D=64, n_nodes=16, gamma=0.01)
        sgm.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        n_antes = len(sgm.omega)
        sgm._engendrar_hijo(0, 1)
        assert len(sgm.omega) == n_antes + 1