# -*- coding: utf-8 -*-
"""Tests de percepción del entorno (0066) — exterocepción, no cuerpo.

La máquina es el ENTORNO de Pandora, no su cuerpo (su cuerpo es el grafo, 0061).
Verifica que:
1. PercepcionEntorno genera un vector sensorial en el espacio del SGM (D correcto).
2. integrar_experiencia_entorno proyecta el patrón al nodo más afín (resonancia).
3. La percepción deja huella (activa el nodo) sin crear nodos de golpe.
4. El análisis espectral corre en numpy puro (sin scipy).
"""
import math
import random

import numpy as np

from sgm.core.sgm_core import SGMAgentCore
from pandora.senses.entorno import PercepcionEntorno
from pandora.senses.espectral import densidad_espectral_potencia, frecuencia_dominante


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


class TestPercepcionEntorno:
    def test_vector_sensorial_dimension_correcta(self):
        """El vector sensorial vive en el mismo espacio D que los conceptos."""
        sgm = make_sgm(D=64)
        pe = PercepcionEntorno(sgm.hrr, D=64)
        vector, carga, _ = pe.percibir()
        assert len(vector) == sgm.D
        assert 0.0 <= carga <= 1.0

    def test_integrar_activa_nodo_afin(self):
        """La percepción resuena con un nodo existente y lo activa leve."""
        sgm = make_sgm(D=64)
        pe = PercepcionEntorno(sgm.hrr, D=64)
        vector, carga, _ = pe.percibir()

        resultado = sgm.integrar_experiencia_entorno(vector, carga)
        assert resultado["seed"] >= 0
        assert resultado["seed"] < len(sgm.omega)
        # La vitalidad del nodo activado subió (la percepción dejó huella)
        assert sgm.vitalidad[resultado["seed"]] > 0.0

    def test_integrar_no_crea_nodos_de_golpe(self):
        """La percepción NO crea nodos nuevos instantáneamente (solo resuena)."""
        sgm = make_sgm(D=64)
        n_antes = len(sgm.omega)
        pe = PercepcionEntorno(sgm.hrr, D=64)
        vector, carga, _ = pe.percibir()
        sgm.integrar_experiencia_entorno(vector, carga)
        assert len(sgm.omega) == n_antes  # sin crear nodo


class TestEspectral:
    def test_frecuencia_dominante_numpy_puro(self):
        """El análisis espectral corre sin scipy (solo numpy + math)."""
        serie = np.array([20 + 10 * np.sin(i / 3) + random.Random(i).gauss(0, 1)
                          for i in range(200)])
        freqs, potencia = densidad_espectral_potencia(serie, window=64)
        assert len(freqs) == len(potencia)
        assert len(freqs) > 0
        f = frecuencia_dominante(serie, window=64)
        assert f is not None

    def test_serie_corta_devuelve_vacio(self):
        """Una serie más corta que la ventana no debería explotar."""
        serie = np.array([1.0, 2.0, 3.0])
        freqs, potencia = densidad_espectral_potencia(serie, window=64)
        assert len(freqs) == 0