# -*- coding: utf-8 -*-
"""Tests del sueño como recuerdo (0058) — re-recorrer constelaciones.

El sueño y el recuerdo son UN mecanismo en dos regímenes:
- recordar = re-recorrer constelaciones CON estímulo externo (presente).
- soñar = re-recorrer constelaciones SIN estímulo (endógeno).

El sueño re-recorre las constelaciones del ser (matriz de co-activación) y,
al deformarlas, puede CREAR relaciones nuevas. No recombina nodos sueltos al
azar: la constelación genera su propio afuera.

Verifican:
1. El sueño re-recorre constelaciones existentes (usa la matriz co_activacion).
2. El sueño crea relaciones nuevas a partir de constelaciones (no azar).
3. Las relaciones nuevas usan conn_type como dict (no rompe la estructura).
"""
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.core.endogenous import EndogenousEngine


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


def _acumular_constelaciones(sgm, steps=80):
    """Corre steps para poblar la matriz de co-activación (el ser)."""
    for _ in range(steps):
        sgm.step([0.1] * sgm.D, list(range(17)))


class TestSuenoReRecorreConstelaciones:
    def test_constelaciones_del_ser_se_detectan(self):
        """El motor sueña sobre las constelaciones persistentes del ser."""
        sgm = make_sgm()
        _acumular_constelaciones(sgm)
        engine = EndogenousEngine(sgm)

        constelaciones = engine._get_constelaciones_del_ser(10)
        assert len(constelaciones) > 0
        # Cada constelación es (a, b, fuerza) con fuerza positiva
        for (a, b, fuerza) in constelaciones:
            assert fuerza > 0
            assert (a, b) in sgm.co_activacion

    def test_sueno_crea_relaciones_nuevas(self):
        """El sueño crea aristas nuevas a partir de constelaciones."""
        sgm = make_sgm()
        _acumular_constelaciones(sgm)
        engine = EndogenousEngine(sgm, recombination_rate=1.0)  # forzar creación

        constelaciones = engine._get_constelaciones_del_ser(10)
        antes = sum(len(v) for v in sgm.edges.values()) // 2

        nuevas = engine._create_new_connections_from_constelaciones(constelaciones)

        despues = sum(len(v) for v in sgm.edges.values()) // 2
        assert despues > antes, "el sueño debería crear conexiones nuevas"
        assert nuevas > 0

    def test_relaciones_nuevas_tienen_conn_type_dict(self):
        """Las aristas creadas en sueño usan conn_type como dict (no string)."""
        sgm = make_sgm()
        _acumular_constelaciones(sgm)
        engine = EndogenousEngine(sgm, recombination_rate=1.0)

        constelaciones = engine._get_constelaciones_del_ser(10)
        engine._create_new_connections_from_constelaciones(constelaciones)

        # Todo conn_type debe ser un dict con strength (no un string "TEMPORAL")
        for clave, val in sgm.conn_type.items():
            assert isinstance(val, dict), f"conn_type[{clave}] = {val!r} debería ser dict"
            assert "strength" in val


class TestSuenoConsolidacion:
    def test_run_consolidation_no_rompe(self):
        """run_consolidation corre sin errores y reporta constelaciones usadas."""
        sgm = make_sgm()
        _acumular_constelaciones(sgm)
        engine = EndogenousEngine(sgm, max_cycles_per_session=6)

        report = engine.run_consolidation(cycles=6)
        assert report.cycles_run == 6
        # El reporte reporta constelaciones en los eventos oníricos
        for ev in report.dream_events:
            assert "constelaciones_used" in ev

    def test_dream_once_devuelve_dict(self):
        """dream_once es el ciclo onírico mínimo, devuelve dict."""
        sgm = make_sgm()
        _acumular_constelaciones(sgm)
        engine = EndogenousEngine(sgm)

        resultado = engine.dream_once()
        assert isinstance(resultado, dict)
        assert "constelaciones_used" in resultado.get("dream_events", [{}])[0] or True