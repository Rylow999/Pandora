# -*- coding: utf-8 -*-
"""Tests de la vivencia espectral (NOTA 0074), resonancia (0073 p2), y
cuerdas de bits (0075).

Verifican: la firma de vivencia se acumula/diverge/persiste, los nodos en fase
resuenan, y la firma binaria (cuerda comprimida) preserva similitud.
"""
import math
import random
import tempfile
import os

from sgm.core.sgm_core import SGMAgentCore
from sgm.core.sgm_vivencia import (
    VivenciaNodo, RegistroVivencia, _dft_magnitudes,
    firma_binaria, distancia_hamming,
)


class TestDFT:
    def test_dft_de_constante_es_dc(self):
        m = _dft_magnitudes([1.0, 1.0, 1.0, 1.0])
        assert abs(m[0] - 4.0) < 1e-6
        assert all(abs(x) < 1e-6 for x in m[1:])

    def test_dft_devuelve_tantas_componentes_como_muestras(self):
        assert len(_dft_magnitudes([1.0, 2.0, 3.0])) == 3


class TestFirmaBinaria:
    def test_produce_bits(self):
        b = firma_binaria([0.1, 0.2, 0.3, 0.4], n_bits=16)
        assert len(b) == 16
        assert all(x in (0, 1) for x in b)

    def test_determinista(self):
        v = [0.5, -0.3, 0.9, 0.1]
        assert firma_binaria(v) == firma_binaria(v)

    def test_preserva_similitud(self):
        """Vectores cercanos -> firmas parecidas (baja Hamming); lejanos -> alta."""
        a = [0.5] * 16
        b = [0.5] * 16
        b[0] = 0.4  # casi igual a a
        c = [-0.5] * 16  # opuesto a a
        d_ab = distancia_hamming(firma_binaria(a), firma_binaria(b))
        d_ac = distancia_hamming(firma_binaria(a), firma_binaria(c))
        assert d_ab < d_ac, f"cercanos {d_ab} debería ser < lejanos {d_ac}"

    def test_cuerda_de_vivencia(self):
        """La cuerda del nodo es la firma binaria de su espectro."""
        v = VivenciaNodo(max_historia=8)
        for _ in range(4):
            v.registrar(0.8, 0.2)
        c = v.cuerda(n_bits=16)
        assert len(c) == 16
        assert all(x in (0, 1) for x in c)


class TestVivenciaNodo:
    def test_firma_se_acumula(self):
        v = VivenciaNodo(max_historia=8)
        assert v.firma()["veces_vivido"] == 0
        v.registrar(0.5, 0.2)
        v.registrar(0.5, 0.2)
        assert v.firma()["veces_vivido"] == 2

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
        reg = RegistroVivencia()
        for _ in range(8):
            reg.registrar(0, 0.8, 0.2)
            reg.registrar(9, 0.8, 0.2)
        for i in range(8):
            reg.registrar(5, -0.8, 0.9)
        resonantes = reg.resonar(0, lambda i, j: 0.0, umbral=0.3)
        ids = [j for j, _ in resonantes]
        assert 9 in ids
        assert 5 not in ids

    def test_mas_en_fase_mas_afinidad(self):
        reg = RegistroVivencia()
        for _ in range(8):
            reg.registrar(0, 0.7, 0.2)
        for _ in range(7):
            reg.registrar(1, 0.7, 0.2)
        reg.registrar(1, 0.6, 0.3)
        for i in range(8):
            reg.registrar(2, 0.5 if i % 2 else 0.9, 0.2)
        resonantes = dict(reg.resonar(0, lambda i, j: 0.0, umbral=0.99))
        assert resonantes[1] > resonantes.get(2, 0.0)


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
        assert len(sgm.vivencias.nodos) > 0

        tmp = tempfile.mktemp(suffix=".npy")
        sgm.guardar(tmp)
        sgm2 = SGMAgentCore(random.Random(99), D=64, n_nodes=16, gamma=0.01)
        sgm2.set_edges({i: random.Random(i).sample(range(16), min(4, 15)) for i in range(16)})
        sgm2.cargar(tmp)
        assert len(sgm2.vivencias.nodos) == len(sgm.vivencias.nodos)
        os.remove(tmp)