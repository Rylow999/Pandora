# -*- coding: utf-8 -*-
"""Tests del presente emergente (phi_root) — NOTA_TECNICA_0060, opción A.

phi_root ya no es 0.0 fijo: es la fase media de la constelación activa,
ponderada por interferencia, que EMERGE del colectivo (Kuramoto ψ) y se ancla
en la coalición ganadora (Dehaene/Baars ignition).

Verifican:
1. El presente se MUEVE (no está congelado en 0.0).
2. El presente converge/estabiliza cuando el sistema se asienta (el ser se ancla).
3. El presente emerge del colectivo (no es un valor impuesto externo).
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


class TestPresenteEmergente:
    def test_phi_root_ya_no_es_cero(self):
        """Tras un tick, phi_root debe haber emergido (≠ 0.0)."""
        sgm = make_sgm()
        assert sgm.phi_root == 0.0  # inicial antes de cualquier step
        sgm.step([0.1] * sgm.D, list(range(17)))
        assert sgm.phi_root != 0.0, "el presente no debería quedarse congelado en 0.0"

    def test_phi_root_circula(self):
        """Durante la sincronización, el presente se mueve (el estar lo mueve)."""
        sgm = make_sgm()
        valores = []
        for _ in range(20):
            sgm.step([0.1] * sgm.D, list(range(17)))
            valores.append(sgm.phi_root)
        # El presente cambió al menos en algún tramo (no es constante)
        assert len(set(round(v, 4) for v in valores)) > 1, \
            "el presente debería circular durante la sincronización"

    def test_phi_root_se_ancla(self):
        """Cuando el sistema se asienta, el presente se estabiliza (el ser se ancla)."""
        sgm = make_sgm()
        # Sincronizar mucho: el sistema converge a coherencia
        for _ in range(150):
            sgm.step([0.1] * sgm.D, list(range(17)))

        # Los últimos ticks el presente casi no se mueve
        ultimos = [sgm.phi_root]
        for _ in range(10):
            sgm.step([0.1] * sgm.D, list(range(17)))
            ultimos.append(sgm.phi_root)

        # Variación entre ticks consecutivos es pequeña (estable)
        max_delta = max(abs(a - b) for a, b in zip(ultimos, ultimos[1:]))
        assert max_delta < 0.05, f"el presente no se estabilizó: delta={max_delta:.4f}"

    def test_phi_root_esta_en_rango(self):
        """phi_root debe vivir en [0, 2π)."""
        sgm = make_sgm()
        for _ in range(30):
            sgm.step([0.1] * sgm.D, list(range(17)))
            assert 0.0 <= sgm.phi_root < 2 * math.pi

    def test_fase_media_ponderada_emerge_del_colectivo(self):
        """phi_root debe ser la fase media de los osciladores alineados (ψ de Kuramoto).

        Cuando todos los nodos están en fase (coherentes), el presente emerge
        como esa fase compartida. No es 0.0 impuesto, es la fase del colectivo.
        """
        sgm = make_sgm()
        # Forzar coherencia total: todas las fases apuntan al mismo lugar
        fase_objetivo = 1.2345
        for i in range(len(sgm.phi)):
            sgm.phi[i] = fase_objetivo
        for i in range(len(sgm.vitalidad)):
            sgm.vitalidad[i] = 1.0

        sgm._actualizar_phi_root()

        # Con todo alineado, la fase media debe ser exactamente la fase objetivo
        assert abs(sgm.phi_root - fase_objetivo) < 1e-3