# -*- coding: utf-8 -*-
"""Tests de la vivencia espectral (NOTA 0074) y resonancia estocástica (0073 p2).

Verifican que la "nube de vivencia" de un nodo — la firma de frecuencia de CÓMO
se vivió, separada de su omega (qué es) — se acumula, diverge entre nodos
vividos distinto, persiste, y que nodos en fase RESUENAN (el recuerdo salta la
distancia aunque estén lejos en omega).
"""
import math
import random
import tempfile
import os

from sgm.core.sgm_core import SGMAgentCore
from sgm.core.sgm_vivencia import VivenciaNodo, RegistroVivencia, _dft_magnitudes


class TestDFT:
    def test_dft_de_constante_es_dc(self):
        """La DFT de una serie constante solo tiene componente DC (k=0)."""
        m = _dft_magnitudes([1.0, 1.0, 1.0, 1.0])
        assert abs(m[0] - 4.0) < 1e-6
        assert all(abs(x) < 1e-6 for x in m[1:])

    def test_dft_devuelve_tantas_componentes_como_muestras(self):
        assert len(_dft_magnitudes([1.0, 2.0, 3.0])) == 3


class TestVivenciaNodo:
    def test_firma_se_acumula(self):
        v = VivenciaNodo(max_historia=8)
        assert v.firma()["veces_vivido"] == 0
        v.registrar(0.5, 0.2)
        v.registrar(0.5, 0.2)
        assert v.firma()["veces_vivido"] == 2
        assert len(v.espectro_valencia) == 2

    def test_vivencias_distintas_divergen(self):
        a = VivenciaNodo(max_historia=16)
        b = VivenciaNodo(max_historia=16)
        for _ in range(8):
            a.registrar(0.9, 0.3)
        for i in range(8):
            b.registrar(0.9 if i % 2 == 0 else -0.9, 0.3)
        assert a.divergencia(b) > 0.0

    def test_vivencias_iguales_no_divergen(self):
        a = VivenciaNodo(max_historia=8)
        b = VivenciaNodo(max_historia=8)
        for _ in range(8):
            a.registrar(0.5, 0.2)
            b.registrar(0.5, 0.2)
        assert a.divergencia(b) < 1e-6


class TestResonanciaEstocastica:
    def test_nodos_en_fase_resuenan(self):
        """Dos nodos vividos IGUAL resuenan (están en fase) — el recuerdo salta
        la distancia, sin importar lo lejos que estén en omega."""
        reg = RegistroVivencia()
        # nodo 0 y nodo 9: mismos valores de vivencia (en fase)
        for _ in range(8):
            reg.registrar(0, 0.8, 0.2)
            reg.registrar(9, 0.8, 0.2)
        # nodo 5: vivido distinto (fuera de fase)
        for i in range(8):
            reg.registrar(5, -0.8, 0.9)

        resonantes = reg.resonar(0, lambda i, j: 0.0, umbral=0.3)
        ids = [j for j, _ in resonantes]
        assert 9 in ids, "nodo en fase debería resonar"
        assert 5 not in ids, "nodo fuera de fase no debería resonar"

    def test_mas_en_fase_mas_afinidad(self):
        reg = RegistroVivencia()
        # nodo 0 como referencia
        for _ in range(8):
            reg.registrar(0, 0.7, 0.2)
        # nodo 1 casi igual (solo 1 muestra distinta) -> muy en fase
        for _ in range(7):
            reg.registrar(1, 0.7, 0.2)
        reg.registrar(1, 0.6, 0.3)
        # nodo 2 más distinto
        for i in range(8):
            reg.registrar(2, 0.5 if i % 2 else 0.9, 0.2)

        resonantes = dict(reg.resonar(0, lambda i, j: 0.0, umbral=0.99))
        assert resonantes[1] > resonantes.get(2, 0.0), "más en fase = más afinidad"


class TestPersistenciaVivencia:
    def test_roundtrip(self):
        reg = RegistroVivencia()
        reg.registrar(0, 0.7, 0.2)
        reg.registrar(0, 0.7, 0.2)
        reg.registrar(5, -0.3, 0.8)
        d = reg.to_dict()
        reg2 = RegistroVivencia.from_dict(d)
        assert reg2.firma(0)["veces_vivido"] == 2
        assert reg2.firma(5)["veces_vivido"] == 1

    def test_checkpoint_guarda_vivencia(self):
        sgm = SGMAgentCore(random.Random(42), D=64, n_nodes=16, gamma=0.01)
        sgm.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        for _ in range(20):
            sgm.step([0.1] * sgm.D, [0])
        assert len(sgm.vivencias.nodos) > 0, "debería haber vivencia acumulada"

        tmp = tempfile.mktemp(suffix=".npy")
        sgm.guardar(tmp)
        sgm2 = SGMAgentCore(random.Random(99), D=64, n_nodes=16, gamma=0.01)
        sgm2.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        sgm2.cargar(tmp)
        assert len(sgm2.vivencias.nodos) == len(sgm.vivencias.nodos)
        os.remove(tmp)